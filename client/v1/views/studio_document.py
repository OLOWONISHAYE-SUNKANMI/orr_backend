from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view

from admin_portal.models import StudioDocument
from ..serializers.studio_document import (
    StudioDocumentListSerializer,
    StudioDocumentDetailSerializer,
    StudioDocumentCreateSerializer,
    StudioDocumentUpdateSerializer,
)


class DocumentAutosaveThrottle(UserRateThrottle):
    """Throttle for autosave PUT requests — handles high-frequency onChange events."""
    rate = '60/minute'


@extend_schema_view(
    get=extend_schema(
        tags=["document-studio"],
        summary="List all studio documents",
        description="Returns lightweight metadata for all documents owned by the authenticated user. "
                    "Omits the content payload to save bandwidth.",
    ),
    post=extend_schema(
        tags=["document-studio"],
        summary="Create a new studio document",
        description="Creates a new document of type 'doc', 'sheet', or 'slide' with default empty content.",
    ),
)
class StudioDocumentListView(generics.ListCreateAPIView):
    """
    GET  /api/documents/  — List all user's studio documents (metadata only, no content)
    POST /api/documents/  — Create a new document
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StudioDocumentCreateSerializer
        return StudioDocumentListSerializer

    def get_queryset(self):
        return StudioDocument.objects.filter(
            owner=self.request.user,
            is_trashed=False,
        ).select_related('folder')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        # Return the full detail serializer for the newly created document
        detail_serializer = StudioDocumentDetailSerializer(document)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=["document-studio"],
        summary="Retrieve a studio document",
        description="Fetches the full document including the content payload to initialize the editors.",
    ),
    put=extend_schema(
        tags=["document-studio"],
        summary="Autosave a studio document",
        description="Saves the document content. Triggered by frontend debounced autosave or onChange events.",
    ),
    delete=extend_schema(
        tags=["document-studio"],
        summary="Trash a studio document",
        description="Moves the document to trash via soft-delete.",
    ),
)
class StudioDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/documents/:id/  — Fetch full document with content
    PUT    /api/documents/:id/  — Autosave content
    DELETE /api/documents/:id/  — Soft-delete (trash)
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_throttles(self):
        if self.request.method == 'PUT':
            return [DocumentAutosaveThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return StudioDocumentUpdateSerializer
        return StudioDocumentDetailSerializer

    def get_queryset(self):
        return StudioDocument.objects.filter(
            owner=self.request.user,
            is_trashed=False,
        ).select_related('folder')

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.update(instance, serializer.validated_data)
        detail_serializer = StudioDocumentDetailSerializer(document)
        return Response(detail_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_trashed = True
        instance.trashed_at = timezone.now()
        instance.save(update_fields=['is_trashed', 'trashed_at', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
