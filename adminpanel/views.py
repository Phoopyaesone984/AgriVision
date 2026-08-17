from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from community.models import Post, PostImage
from community.forms import PostForm
from .decorators import staff_required


@staff_required
def dashboard(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.status = Post.STATUS_APPROVED
            post.save()
            form.save_m2m()
            for i, f in enumerate(request.FILES.getlist("images")):
                PostImage.objects.create(post=post, image=f, order=i)
            messages.success(request, "Official post broadcasted to Community!")
            return redirect("adminpanel:dashboard")
    else:
        form = PostForm()

    users = (
        User.objects.select_related("profile")
        .annotate(total_posts=Count("posts"))
        .order_by("-date_joined")
    )

    q = request.GET.get("q", "").strip()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))

    status = request.GET.get("status", "")
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "post_form": form,
        "page_obj": page_obj,
        "q": q,
        "active_status": status,
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_posts": Post.objects.count(),
    }
    return render(request, "admin_dashboard.html", context)


@staff_required
@require_POST
def toggle_user_active(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("adminpanel:dashboard")

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=["is_active"])
    messages.success(request, f"User {user_obj.username} status updated.")
    return redirect("adminpanel:dashboard")


@staff_required
def get_user_posts_json(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    posts = Post.objects.filter(author=user_obj).prefetch_related("images", "comments").order_by("-created_at")

    posts_data = []
    for p in posts:
        images = [img.image.url for img in p.images.all()]
        posts_data.append({
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "created_at": p.created_at.strftime("%b %d, %Y · %H:%M"),
            "likes": p.likes.count(),
            "comments": p.comments.count(),
            "images": images,
        })

    return JsonResponse({
        "username": user_obj.get_full_name() or user_obj.username,
        "posts": posts_data,
        "total": len(posts_data),
    })


@staff_required
def get_user_posts_json(request, pk):
    user_obj = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    posts = Post.objects.filter(author=user_obj).prefetch_related("images", "comments").order_by("-created_at")

    posts_data = []
    for p in posts:
        images = [img.image.url for img in p.images.all()]
        posts_data.append({
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "created_at": p.created_at.strftime("%b %d, %Y · %H:%M"),
            "likes": p.likes.count(),
            "comments": p.comments.count(),
            "images": images,
        })

    # Profile Data Extract လုပ်ခြင်း
    profile = getattr(user_obj, "profile", None)
    avatar_url = profile.avatar.url if profile and profile.avatar else None

    return JsonResponse({
        "user_id": user_obj.id,
        "username": user_obj.username,
        "full_name": user_obj.get_full_name() or user_obj.username,
        "email": user_obj.email or "—",
        "phone": getattr(profile, "phone_number", "—") or "—",
        "location": getattr(profile, "location", "—") or "—",
        "bio": getattr(profile, "bio", "") or "No bio provided.",
        "avatar": avatar_url,
        "role_title": getattr(profile, "role_title", "Farmer") or "Farmer",
        "is_active": user_obj.is_active,
        "is_staff": user_obj.is_staff,
        "date_joined": user_obj.date_joined.strftime("%B %d, %Y"),
        "posts": posts_data,
        "total": len(posts_data),
    })

@staff_required
@require_POST
def delete_post_admin(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.delete()
    return JsonResponse({"success": True})