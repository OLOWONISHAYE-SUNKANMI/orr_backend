from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import Content
from admin_portal.permissions import CanCreateContent, CanPublishContent

from ..serializers.content import (
    ContentCreateUpdateSerializer,
    ContentDetailSerializer,
    ContentListSerializer,
    ContentPublishSerializer,
    ContentStatsSerializer,
)


@extend_schema(
    tags=["Content Management"],
    summary="List or create content",
    description="Retrieve a filtered list of content items (FAQs, articles, checklists, templates, guides) or create new content. Supports filtering by type, status, stage, pillar, and author.",
)
class ContentListView(generics.ListCreateAPIView):
    """List and create content"""

    permission_classes = [CanCreateContent]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ContentCreateUpdateSerializer
        return ContentListSerializer

    def get_queryset(self):
        queryset = Content.objects.select_related("author").all()

        # Search functionality
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(summary__icontains=search)
                | Q(content__icontains=search)
            )

        # Filters
        content_type = self.request.query_params.get("type", None)
        if content_type:
            queryset = queryset.filter(content_type=content_type)

        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        stage = self.request.query_params.get("stage", None)
        if stage:
            queryset = queryset.filter(stage=stage)

        pillar = self.request.query_params.get("pillar", None)
        if pillar:
            queryset = queryset.filter(pillars__contains=[pillar])

        author = self.request.query_params.get("author", None)
        if author:
            queryset = queryset.filter(author_id=author)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        # Set published_at if status is published
        validated_data = serializer.validated_data
        if validated_data.get('status') == 'published':
            from django.utils import timezone
            validated_data['published_at'] = timezone.now()
        
        serializer.save(author=self.request.user)


@extend_schema(
    tags=["Content Management"],
    summary="Manage content item",
    description="Retrieve, update, or delete a specific content item including its metadata, attachments, and categorization.",
)
class ContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete content"""

    queryset = Content.objects.select_related("author").all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ContentDetailSerializer
        return ContentCreateUpdateSerializer


@extend_schema(
    tags=["Content Management"],
    summary="Publish content actions",
    description="Perform publishing actions on content including publish, unpublish, or archive. Creates audit logs for all publishing actions.",
)
class ContentPublishView(APIView):
    """Publish, unpublish, or archive content"""

    permission_classes = [CanPublishContent]

    def post(self, request, pk):
        try:
            content = Content.objects.get(pk=pk)
            serializer = ContentPublishSerializer(data=request.data)

            if serializer.is_valid():
                action = serializer.validated_data["action"]

                if action == "publish":
                    content.status = "published"
                    content.published_at = timezone.now()
                    message = "Content published successfully"
                elif action == "unpublish":
                    content.status = "draft"
                    content.published_at = None
                    message = "Content unpublished successfully"
                elif action == "archive":
                    content.status = "archived"
                    message = "Content archived successfully"

                content.save()

                # Create audit log
                from admin_portal.models import AuditLog

                AuditLog.objects.create(
                    user=request.user,
                    action="publish" if action == "publish" else "archive",
                    model_name="Content",
                    object_id=str(content.pk),
                    description=f"{action.title()} content: {content.title}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                return Response({"message": message, "status": content.status})

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Content.DoesNotExist:
            return Response(
                {"error": "Content not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Content Management"],
    summary="Preview content for clients",
    description="Preview how content will appear to clients in the portal, including formatted display of title, summary, content, and attachments.",
)
class ContentPreviewView(APIView):
    """Preview content as it would appear to clients"""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            content = Content.objects.get(pk=pk)

            # Return content formatted for client view
            preview_data = {
                "title": content.title,
                "summary": content.summary,
                "content": content.content,
                "type": content.get_content_type_display(),
                "stage": content.get_stage_display(),
                "pillars": [
                    dict(Content.PILLAR_CHOICES).get(p, p) for p in content.pillars
                ],
                "attachment_url": (
                    content.attachment.url if content.attachment else None
                ),
                "published_at": content.published_at,
            }

            return Response(preview_data)

        except Content.DoesNotExist:
            return Response(
                {"error": "Content not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Content Management"],
    summary="Get content statistics",
    description="Retrieve comprehensive content analytics including counts by type/status/stage/pillar, most viewed/downloaded content, and content gaps analysis.",
)
class ContentStatsView(APIView):
    """Content statistics and analytics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Basic content counts
        total_content = Content.objects.count()
        published_content = Content.objects.filter(status="published").count()
        draft_content = Content.objects.filter(status="draft").count()
        archived_content = Content.objects.filter(status="archived").count()

        # Content by type
        content_by_type = dict(
            Content.objects.values("content_type")
            .annotate(count=Count("id"))
            .values_list("content_type", "count")
        )

        # Content by stage
        content_by_stage = dict(
            Content.objects.values("stage")
            .annotate(count=Count("id"))
            .values_list("stage", "count")
        )

        # Content by pillar (this is more complex due to JSONField)
        content_by_pillar = {}
        for pillar_code, pillar_name in Content.PILLAR_CHOICES:
            count = Content.objects.filter(pillars__contains=[pillar_code]).count()
            content_by_pillar[pillar_code] = count

        # Most viewed content
        most_viewed = Content.objects.filter(status="published").order_by(
            "-view_count"
        )[:5]
        most_viewed_data = [
            {"id": c.id, "title": c.title, "view_count": c.view_count}
            for c in most_viewed
        ]

        # Most downloaded content
        most_downloaded = Content.objects.filter(
            status="published", attachment__isnull=False
        ).order_by("-download_count")[:5]
        most_downloaded_data = [
            {"id": c.id, "title": c.title, "download_count": c.download_count}
            for c in most_downloaded
        ]

        stats_data = {
            "total_content": total_content,
            "published_content": published_content,
            "draft_content": draft_content,
            "archived_content": archived_content,
            "content_by_type": content_by_type,
            "content_by_stage": content_by_stage,
            "content_by_pillar": content_by_pillar,
            "most_viewed": most_viewed_data,
            "most_downloaded": most_downloaded_data,
        }

        serializer = ContentStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema(
    tags=["Content Management"],
    summary="Manage content versions",
    description="Create new versions of content items and track version history with audit logging.",
)
class ContentVersionsView(APIView):
    """Manage content versions"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            content = Content.objects.get(pk=pk)
            action = request.data.get("action")

            if action == "create_version":
                # Create a new version of the content
                content.version += 1
                content.save()

                # Create audit log
                from admin_portal.models import AuditLog

                AuditLog.objects.create(
                    user=request.user,
                    action="update",
                    model_name="Content",
                    object_id=str(content.pk),
                    description=f"Created version {content.version} of content: {content.title}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                return Response(
                    {
                        "message": f"Created version {content.version}",
                        "version": content.version,
                    }
                )

            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

        except Content.DoesNotExist:
            return Response(
                {"error": "Content not found"}, status=status.HTTP_404_NOT_FOUND
            )


from admin_portal.permissions import IsSuperAdmin

@extend_schema(
    tags=["Content Management"],
    summary="Perform bulk content actions",
    description="Execute bulk operations on multiple content items including bulk publish, archive, or delete with audit logging.",
)
class ContentBulkActionsView(APIView):
    """Bulk actions for content management"""

    permission_classes = [IsSuperAdmin]

    def post(self, request):
        action = request.data.get("action")
        content_ids = request.data.get("content_ids", [])

        if not content_ids:
            return Response(
                {"error": "No content IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        contents = Content.objects.filter(id__in=content_ids)

        if action == "bulk_publish":
            contents.update(status="published", published_at=timezone.now())
            message = f"Published {contents.count()} content items"
        elif action == "bulk_archive":
            contents.update(status="archived")
            message = f"Archived {contents.count()} content items"
        elif action == "bulk_delete":
            count = contents.count()
            contents.delete()
            message = f"Deleted {count} content items"
        else:
            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create audit log
        from admin_portal.models import AuditLog

        AuditLog.objects.create(
            user=request.user,
            action=action.replace("bulk_", ""),
            model_name="Content",
            description=message,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response({"message": message})


@extend_schema(
    tags=["Content Management"],
    summary="Increment content view count",
    description="Increment the view count for a specific content item when it is accessed.",
)
class ContentViewCountView(APIView):
    """Increment view count for content"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            content = Content.objects.get(pk=pk)
            content.view_count += 1
            content.save(update_fields=['view_count'])
            
            return Response({
                "message": "View count incremented",
                "view_count": content.view_count
            })

        except Content.DoesNotExist:
            return Response(
                {"error": "Content not found"}, status=status.HTTP_404_NOT_FOUND
            )
