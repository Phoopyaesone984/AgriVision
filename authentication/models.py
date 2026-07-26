from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(
        max_length=100,
        blank=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    role_title = models.CharField(max_length=80, blank=True,
                                  help_text="e.g. 'Senior Agronomist' or 'Farmer, Bago Region'")

    def __str__(self):
        return self.user.username