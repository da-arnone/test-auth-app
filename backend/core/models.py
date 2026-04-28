import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class AppUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def verify_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.ForeignKey(AppUser, related_name="profiles", on_delete=models.CASCADE)
    app_scope = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    context = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "app_scope", "role", "context"], name="unique_profile_per_user"
            )
        ]

    def __str__(self):
        ctx = self.context or "-"
        return f"{self.user.username}:{self.app_scope}/{self.role}/{ctx}"
