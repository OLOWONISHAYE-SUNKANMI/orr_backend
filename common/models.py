from django.db import models
from django.conf import settings
from .thread_local_middleware import get_current_user

class Audit(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s_updated")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk and getattr(self, 'created_by', None) is None:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
