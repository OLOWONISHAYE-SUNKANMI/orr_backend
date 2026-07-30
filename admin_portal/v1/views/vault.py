from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Count

from admin_portal.models import ClientDocument, VaultFolder, Client
from drf_spectacular.utils import extend_schema


# ---------------------------------------------------------------------------
# Serializers (inline – no separate file needed)
# ---------------------------------------------------------------------------

from rest_framework import serializers


class VaultFolderSerializer(serializers.ModelSerializer):
    doc_count = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    client_name = serializers.SerializerMethodField()

    class Meta:
        model = VaultFolder
        fields = ['id', 'name', 'parent', 'client', 'client_name', 'project', 'doc_count', 'created_at', 'updated_at']

    def get_doc_count(self, obj):
        return getattr(obj, 'annotated_doc_count', 0)

    def get_client_name(self, obj):
        # client__user already fetched via select_related
        try:
            if obj.client_id and obj.client and obj.client.user:
                return obj.client.user.get_full_name() or obj.client.user.username
        except Exception:
            pass
        return ''


class VaultFolderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaultFolder
        fields = ['id', 'name', 'parent', 'client', 'project']

    def validate_client(self, value):
        return value

    def validate_parent(self, value):
        return value


class VaultDocumentSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    folder_id = serializers.IntegerField(read_only=True)
    file_size = serializers.SerializerMethodField()
    name = serializers.CharField(source='title')
    client_name = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = ClientDocument
        fields = [
            'id', 'name', 'title', 'description', 'link', 'document_type', 'document_source',
            'google_drive_id', 'category', 'visibility', 'folder', 'folder_id',
            'file_size', 'client', 'client_name', 'project', 'created_at', 'updated_at',
        ]

    def get_link(self, obj):
        request = self.context.get('request')
        return obj.get_document_link(request)

    def get_file_size(self, obj):
        size = obj.file_size
        # Removed self-healing DB write — file_size is populated on save()
        if size:
            if size < 1024:
                return f'{size} B'
            elif size < 1024 * 1024:
                return f'{size // 1024} KB'
            else:
                return f'{size // (1024 * 1024)} MB'
        return '0 KB'

    def get_client_name(self, obj):
        # client__user already fetched via select_related
        try:
            if obj.client_id and obj.client and obj.client.user:
                return obj.client.user.get_full_name() or obj.client.user.username
        except Exception:
            pass
        return ''

    def get_project(self, obj):
        # folder already fetched via select_related
        if obj.folder_id and obj.folder:
            return obj.folder.project or ''
        return ''


class VaultDocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDocument
        fields = [
            'id', 'title', 'description', 'category', 'document',
            'document_type', 'document_source', 'google_drive_id',
            'visibility', 'client', 'folder',
        ]

    def validate_client(self, value):
        return value


# ---------------------------------------------------------------------------
# Helper: get client from request user (cached on user object)
# ---------------------------------------------------------------------------

def _get_client(user):
    """Return the Client object for this user, or None. Cached per-request."""
    if not hasattr(user, '_cached_client_profile'):
        user._cached_client_profile = Client.objects.filter(user=user).select_related('user').first()
    return user._cached_client_profile


def _is_admin(user):
    return hasattr(user, 'admin_profile')


# ---------------------------------------------------------------------------
# Shared queryset builders with proper select_related and defer
# ---------------------------------------------------------------------------

def _build_document_queryset(base_qs):
    """Apply select_related and defer heavy fields for list views."""
    return base_qs.select_related(
        'client__user', 'folder', 'uploaded_by'
    ).defer(
        'access_rule_description', 'access_rule_linked_id'
    ).order_by('-updated_at')


def _build_folder_queryset(base_qs):
    """Apply select_related and annotate doc_count for folder lists."""
    return base_qs.select_related(
        'client__user', 'parent'
    ).annotate(
        annotated_doc_count=Count('documents')
    ).order_by('-updated_at')


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def _paginate(queryset, request):
    """
    Lightweight manual pagination.
    Accepts ?page=1&page_size=100 query params.
    Returns (page_qs, pagination_meta).
    """
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(500, max(1, int(request.query_params.get('page_size', 200))))
    except (ValueError, TypeError):
        page_size = 200

    total = queryset.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    page_qs = queryset[offset:offset + page_size]

    return page_qs, {
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': total_pages,
    }


# ---------------------------------------------------------------------------
# VaultFolderListView  – GET list / POST create
# ---------------------------------------------------------------------------

@extend_schema(tags=["vault"])
class VaultFolderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if _is_admin(user):
            client_id = request.query_params.get('client_id')
            if client_id:
                folders = VaultFolder.objects.filter(client_id=client_id)
            else:
                folders = VaultFolder.objects.all()
        else:
            client = _get_client(user)
            if not client:
                return Response(
                    {"status": "error", "message": "Client profile not found."},
                    status=status.HTTP_403_FORBIDDEN
                )
            folders = VaultFolder.objects.filter(client=client)

        folders = _build_folder_queryset(folders)
        serializer = VaultFolderSerializer(folders, many=True, context={'request': request})
        return Response({"status": "success", "data": serializer.data})

    def post(self, request):
        user = request.user
        data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        if _is_admin(user):
            # Admin can specify client explicitly
            client_id = data.get('client') or data.get('client_id')
            if client_id:
                try:
                    client = Client.objects.get(pk=client_id)
                    data['client'] = client.id
                except Client.DoesNotExist:
                    return Response(
                        {"status": "error", "message": "Client not found."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            client = _get_client(user)
            if not client:
                return Response(
                    {"status": "error", "message": "Client profile not found."},
                    status=status.HTTP_403_FORBIDDEN
                )
            data['client'] = client.id

        # Resolve parent
        parent_id = data.get('parent')
        if parent_id:
            try:
                parent_folder = VaultFolder.objects.get(pk=parent_id)
                data['parent'] = parent_folder.id
            except VaultFolder.DoesNotExist:
                data['parent'] = None

        serializer = VaultFolderCreateSerializer(data=data)
        if serializer.is_valid():
            folder = serializer.save()
            return Response(
                {"status": "success", "data": VaultFolderSerializer(folder, context={'request': request}).data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"status": "error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# ---------------------------------------------------------------------------
# VaultFolderDetailView  – GET single / PATCH update / DELETE
# ---------------------------------------------------------------------------

@extend_schema(tags=["vault"])
class VaultFolderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_folder(self, pk, user):
        try:
            folder = VaultFolder.objects.select_related('client__user', 'parent').get(pk=pk)
        except VaultFolder.DoesNotExist:
            return None, "Folder not found."

        if _is_admin(user):
            return folder, None

        client = _get_client(user)
        if not client or folder.client_id != client.id:
            return None, "You do not have permission to access this folder."

        return folder, None

    def get(self, request, pk):
        folder, err = self._get_folder(pk, request.user)
        if err:
            return Response({"status": "error", "message": err}, status=status.HTTP_403_FORBIDDEN)
        if not folder:
            return Response({"status": "error", "message": "Folder not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VaultFolderSerializer(folder, context={'request': request})
        return Response({"status": "success", "data": serializer.data})

    def patch(self, request, pk):
        folder, err = self._get_folder(pk, request.user)
        if err:
            return Response({"status": "error", "message": err}, status=status.HTTP_403_FORBIDDEN)
        if not folder:
            return Response({"status": "error", "message": "Folder not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VaultFolderCreateSerializer(folder, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": VaultFolderSerializer(folder, context={'request': request}).data})
        return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        folder, err = self._get_folder(pk, request.user)
        if err:
            return Response({"status": "error", "message": err}, status=status.HTTP_403_FORBIDDEN)
        if not folder:
            return Response({"status": "error", "message": "Folder not found."}, status=status.HTTP_404_NOT_FOUND)

        # Orphan documents instead of deleting them
        ClientDocument.objects.filter(folder=folder).update(folder=None)
        # Orphan child folders
        VaultFolder.objects.filter(parent=folder).update(parent=None)
        folder.delete()
        return Response({"status": "success", "message": "Folder deleted."}, status=status.HTTP_204_NO_CONTENT)




@extend_schema(tags=["vault"])
class VaultDocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if _is_admin(user):
            client_id = request.query_params.get('client_id')
            visibility = request.query_params.get('visibility')
            if client_id:
                docs = ClientDocument.objects.filter(client_id=client_id)
            else:
                docs = ClientDocument.objects.all()
            # Server-side visibility filter for admin
            if visibility in ('client', 'internal'):
                docs = docs.filter(visibility=visibility)
        else:
            client = _get_client(user)
            if not client:
                return Response(
                    {"status": "error", "message": "Client profile not found."},
                    status=status.HTTP_403_FORBIDDEN
                )
            docs = ClientDocument.objects.filter(client=client, is_visible_to_client=True)

        docs = _build_document_queryset(docs)

        # Pagination
        page_qs, pagination = _paginate(docs, request)
        serializer = VaultDocumentSerializer(page_qs, many=True, context={'request': request})
        return Response({
            "status": "success",
            "data": serializer.data,
            "pagination": pagination,
        })

    def post(self, request):
        user = request.user
        data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        if _is_admin(user):
            client_id = data.get('client') or data.get('client_id')
            if not client_id:
                return Response(
                    {"status": "error", "message": "client_id is required for admin uploads."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                return Response(
                    {"status": "error", "message": "Client not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            client = _get_client(user)
            if not client:
                return Response(
                    {"status": "error", "message": "Client profile not found."},
                    status=status.HTTP_403_FORBIDDEN
                )

        data['client'] = client.id

        # Determine document_source if not provided
        if 'document_source' not in data or not data.get('document_source'):
            data['document_source'] = 'file'

        # Handle folder
        folder_id = data.get('folder')
        if folder_id:
            try:
                folder = VaultFolder.objects.get(pk=folder_id)
                data['folder'] = folder.id
            except VaultFolder.DoesNotExist:
                data.pop('folder', None)

        serializer = VaultDocumentCreateSerializer(data=data)
        if serializer.is_valid():
            doc = serializer.save(uploaded_by=user, is_visible_to_client=True)
            return Response(
                {"status": "success", "data": VaultDocumentSerializer(doc, context={'request': request}).data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"status": "error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# ---------------------------------------------------------------------------
# VaultDocumentDetailView – GET single document
# ---------------------------------------------------------------------------

@extend_schema(tags=["vault"])
class VaultDocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_doc(self, pk, user):
        try:
            doc = ClientDocument.objects.select_related(
                'client__user', 'folder', 'uploaded_by'
            ).get(pk=pk)
        except ClientDocument.DoesNotExist:
            return None, None

        if _is_admin(user):
            return doc, None

        client = _get_client(user)
        if not client or doc.client_id != client.id:
            return None, "You do not have permission to access this document."

        if not doc.is_visible_to_client:
            return None, "This document is not available."

        return doc, None

    def get(self, request, pk):
        doc, err = self._get_doc(pk, request.user)
        if err:
            return Response({"status": "error", "message": err}, status=status.HTTP_403_FORBIDDEN)
        if not doc:
            return Response({"status": "error", "message": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VaultDocumentSerializer(doc, context={'request': request})
        return Response({"status": "success", "data": serializer.data})

    def patch(self, request, pk):
        doc, err = self._get_doc(pk, request.user)
        if err:
            return Response({"status": "error", "message": err}, status=status.HTTP_403_FORBIDDEN)
        if not doc:
            return Response({"status": "error", "message": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VaultDocumentCreateSerializer(doc, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": VaultDocumentSerializer(doc, context={'request': request}).data})
        return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        doc, err = self._get_doc(pk, request.user)
        if err:
            return Response({"status": "error", "message": err}, status=status.HTTP_403_FORBIDDEN)
        if not doc:
            return Response({"status": "error", "message": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        doc.delete()
        return Response({"status": "success", "message": "Document deleted."}, status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# VaultActivityListView – basic activity log placeholder
# ---------------------------------------------------------------------------

@extend_schema(tags=["vault"])
class VaultActivityListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if _is_admin(user):
            client_id = request.query_params.get('client_id')
            if client_id:
                docs = ClientDocument.objects.filter(client_id=client_id)
            else:
                docs = ClientDocument.objects.all()
        else:
            client = _get_client(user)
            if not client:
                return Response({"status": "success", "data": []})
            docs = ClientDocument.objects.filter(client=client)

        # Apply select_related BEFORE slicing for optimal query
        docs = docs.select_related('uploaded_by').order_by('-updated_at')[:20]

        activities = []
        for doc in docs:
            uploaded_by_user = doc.uploaded_by
            user_name = "System"
            if uploaded_by_user:
                user_name = uploaded_by_user.get_full_name() or uploaded_by_user.username

            activities.append({
                "id": doc.id,
                "user": user_name,
                "action": "uploaded" if doc.document_source == 'file' else "created",
                "item": doc.title,
                "description": f"{doc.document_source} document",
                "timestamp": doc.updated_at.isoformat() if doc.updated_at else None,
                "time": doc.updated_at.strftime('%H:%M') if doc.updated_at else '',
                "model": "ClientDocument",
            })

        return Response({"status": "success", "data": activities})


# ---------------------------------------------------------------------------
# batch_update_documents – admin batch operation
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(tags=["vault"])
def batch_update_documents(request):
    if not _is_admin(request.user):
        return Response(
            {"status": "error", "message": "Admin access required."},
            status=status.HTTP_403_FORBIDDEN
        )

    document_ids = request.data.get('document_ids', [])
    action = request.data.get('action')

    if not document_ids or not action:
        return Response(
            {"status": "error", "message": "document_ids and action are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    docs = ClientDocument.objects.filter(pk__in=document_ids)

    if action == 'delete':
        count = docs.count()
        docs.delete()
        return Response({"status": "success", "message": f"Deleted {count} documents."})
    elif action == 'hide':
        docs.update(is_visible_to_client=False)
        return Response({"status": "success", "message": "Documents hidden from clients."})
    elif action == 'show':
        docs.update(is_visible_to_client=True)
        return Response({"status": "success", "message": "Documents made visible to clients."})
    else:
        return Response(
            {"status": "error", "message": f"Unknown action: {action}"},
            status=status.HTTP_400_BAD_REQUEST
        )