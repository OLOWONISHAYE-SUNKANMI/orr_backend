from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from ...models import BlogPost
from ..serializers.blog import BlogPostSerializer


@extend_schema(tags=["main page"])
class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]  # public marketing blog
    queryset = BlogPost.objects.filter(published_at__lte=timezone.now())
    serializer_class = BlogPostSerializer
    lookup_field = "slug"
    ordering_fields = ["published_at", "title"]
