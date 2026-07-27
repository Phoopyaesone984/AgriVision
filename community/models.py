from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Material Symbols icon name, e.g. 'science'")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    color = models.CharField(
        max_length=20,
        choices=[("neutral", "Neutral"), ("mint", "Mint"), ("alert", "Alert")],
        default="neutral",
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Post by {self.author} at {self.created_at:%Y-%m-%d}"

    def get_absolute_url(self):
        return reverse("community:post_detail", args=[self.pk])

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="posts/%Y/%m/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on post {self.post_id}"

    @property
    def like_count(self):
        return self.likes.count()


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_post_like",
                                     condition=models.Q(post__isnull=False)),
            models.UniqueConstraint(fields=["user", "comment"], name="unique_comment_like",
                                     condition=models.Q(comment__isnull=False)),
        ]


from django.urls import reverse

class Notification(models.Model):
    LIKE_POST = "like_post"
    COMMENT_POST = "comment_post"
    LIKE_COMMENT = "like_comment"
    REPLY_COMMENT = "reply_comment"
    VERB_CHOICES = [
        (LIKE_POST, "liked your post"),
        (COMMENT_POST, "commented on your post"),
        (LIKE_COMMENT, "liked your comment"),
        (REPLY_COMMENT, "replied to your comment"),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    verb = models.CharField(max_length=20, choices=VERB_CHOICES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        if self.post_id:
            return reverse("community:notification_redirect", args=[self.pk])
        return reverse("community:feed")