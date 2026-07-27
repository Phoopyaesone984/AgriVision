from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import PostForm, CommentForm
from .models import Post, PostImage, Comment, Like, Category,Notification


def feed(request):
    if request.method == "POST" and request.user.is_authenticated:
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            for i, f in enumerate(request.FILES.getlist("images")):
                PostImage.objects.create(post=post, image=f, order=i)
            return redirect("community:feed")
    else:
        form = PostForm()

    posts = (
        Post.objects.select_related("author", "author__profile", "category")
        .prefetch_related("images", "tags")
        .annotate(n_likes=Count("likes", distinct=True))
    )

    category_slug = request.GET.get("category")
    if category_slug:
        posts = posts.filter(category__slug=category_slug)

    sort = request.GET.get("sort", "new")
    if sort == "top":
        posts = posts.order_by("-n_likes", "-created_at")
    else:
        posts = posts.order_by("-created_at")

    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    liked_post_ids = set()
    if request.user.is_authenticated:
        liked_post_ids = set(
            Like.objects.filter(user=request.user, post__in=page_obj).values_list("post_id", flat=True)
        )

    return render(request, "feed.html", {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "post_form": form,
        "liked_post_ids": liked_post_ids,
        "active_category": category_slug,
        "active_sort": sort,
        "hide_app_sidebar": True,
    })


def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author", "author__profile", "category").prefetch_related("images", "tags"),
        pk=pk,
    )

    csort = request.GET.get("csort", "top")
    comments = (
        post.comments.filter(parent__isnull=True)
        .select_related("author", "author__profile")
        .prefetch_related("replies__author__profile", "replies__likes")
        .annotate(n_likes=Count("likes", distinct=True))
    )
    if csort == "top":
        comments = comments.order_by("-n_likes", "created_at")
    else:
        comments = comments.order_by("created_at")

    liked_comment_ids = set()
    if request.user.is_authenticated:
        liked_comment_ids = set(
            Like.objects.filter(user=request.user, comment__post=post).values_list("comment_id", flat=True)
        )

    return render(request, "post_detail.html", {
        "post": post,
        "comments": comments,
        "comment_form": CommentForm(),
        "liked_comment_ids": liked_comment_ids,
        "active_csort": csort,
        "post_is_liked": request.user.is_authenticated and post.likes.filter(user=request.user).exists(),
        "hide_app_sidebar": True,
    })

@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    parent_id = request.POST.get("parent_id")
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        if parent_id:
            comment.parent = get_object_or_404(Comment, pk=parent_id, post=post)
        comment.save()

        if comment.parent:
            recipient = comment.parent.author
            verb = Notification.REPLY_COMMENT
        else:
            recipient = post.author
            verb = Notification.COMMENT_POST

        if recipient != request.user:
            Notification.objects.create(
                recipient=recipient,
                actor=request.user,
                verb=verb,
                post=post,
                comment=comment,
            )

    return redirect("community:post_detail", pk=pk)
@login_required
@require_POST
def toggle_like(request, model_name, pk):
    if model_name == "post":
        obj = get_object_or_404(Post, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, post=obj)
        recipient = obj.author
        verb = Notification.LIKE_POST
    elif model_name == "comment":
        obj = get_object_or_404(Comment, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, comment=obj)
        recipient = obj.author
        verb = Notification.LIKE_COMMENT
    else:
        return HttpResponseForbidden()

    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if recipient != request.user:
            Notification.objects.create(
                recipient=recipient,
                actor=request.user,
                verb=verb,
                post=obj if model_name == "post" else obj.post,
                comment=obj if model_name == "comment" else None,
            )

    return JsonResponse({"liked": liked, "count": obj.likes.count()})

@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    return redirect("community:feed")


from django.utils.timesince import timesince


@login_required
def notifications_dropdown(request):
    notifications = (
        request.user.notifications
        .select_related("actor", "actor__profile", "post")[:15]
    )
    data = []
    for n in notifications:
        avatar = ""
        if getattr(n.actor, "profile", None) and n.actor.profile.avatar:
            avatar = n.actor.profile.avatar.url
        data.append({
            "id": n.id,
            "actor_name": n.actor.get_full_name() or n.actor.username,
            "actor_initials": n.actor.username[:2].upper(),
            "actor_avatar": avatar,
            "verb": n.get_verb_display(),
            "url": n.get_absolute_url(),
            "is_read": n.is_read,
            "time": timesince(n.created_at) + " ago",
        })
    unread_count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"notifications": data, "unread_count": unread_count})


@login_required
@require_POST
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({"success": True})


@login_required
def notification_redirect(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    if notification.post_id:
        return redirect("community:post_detail", pk=notification.post_id)
    return redirect("community:feed")