from typing import TYPE_CHECKING
from django.db import models

if TYPE_CHECKING:
    from django.contrib.auth.models import User

class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=512)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=512)

    class Meta:
        abstract = True

    def on_behalf_of(self, user: 'User'):
        self.created_by = self.created_by or user.username
        self.updated_by = user.username
        return self

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user:
            self.on_behalf_of(user)
        super().save(*args, **kwargs)