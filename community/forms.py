from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "category", "tags"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "field-input",
                "placeholder": "Add a title (optional)",
            }),
            "content": forms.Textarea(attrs={
                "class": "field-textarea",
                "rows": 3,
                "placeholder": "Share a farm update, ask a question, or write a guide...",
            }),
            "category": forms.Select(attrs={"class": "field-select"}),
            "tags": forms.SelectMultiple(attrs={"class": "field-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "No category"
        self.fields["tags"].required = False
        self.fields["title"].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.TextInput(attrs={
                "class": "comment-input",
                "placeholder": "Write a comment...",
            }),
        }