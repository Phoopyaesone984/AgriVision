from django.contrib import admin
from .models import Category, Tag, Post, PostImage, Comment, Like


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title_or_snippet", "author", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "content", "author__username")
    inlines = [PostImageInline]

    def title_or_snippet(self, obj):
        return obj.title or obj.content[:50]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "parent", "created_at")
    search_fields = ("content", "author__username")


admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Like)