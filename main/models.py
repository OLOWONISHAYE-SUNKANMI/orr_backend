from datetime import timedelta

from django.db import models
from django.utils import timezone

from common.models import Audit


class ContactMessage(Audit):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.subject}"


class BlogPost(Audit):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to="blogs/", blank=True, null=True)
    category = models.CharField()
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class AnalyticsCaseStudy(models.Model):
    title = models.CharField(max_length=200, default="Analytics Case Studies")
    active_users = models.IntegerField(default=0)
    questions_answered = models.IntegerField(default=0)
    avg_session_length = models.DurationField(default="00:00:00")
    starting_knowledge = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    current_knowledge = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    knowledge_gain = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    monthly_activity = models.JSONField(default=dict)

    def __str__(self):
        return self.title


class IndustryInsight(Audit):
    title = models.CharField(max_length=200, default="Industry Specific Insights")
    real_time_users = models.PositiveIntegerField(default=0)
    total_visits = models.PositiveIntegerField(default=0)
    visit_duration = models.DurationField(default=timedelta(0))
    top_countries = models.JSONField(default=list)
    engagement_data = models.JSONField(default=dict)
