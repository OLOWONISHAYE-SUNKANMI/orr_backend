from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q

from admin_portal.models import ClientDocument, VaultFolder, Client
from drf_spectacular.utils import extend_schema


# ---------------------------------------------------------------------------
# Serializers (inline – no separate file needed)
# ---------------------------------------------------------------------------

from rest_framework import serializers


class VaultFolderSerializer(serializers.ModelSerializer):
    doc_count = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = VaultFolder
        fields = ['id', 'name', 'parent', 'doc_count', 'created_at', 'updated_at']

    def get_doc_count(self, obj):
        return obj.documents.count()


class VaultFolderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaultFolder
        fields = ['id', 'name', 'parent', 'client']

    def validate_client(self, value):
        return value

    def validate_parent(self, value):
        return value


class VaultDocumentSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    folder_id = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    name = serializers.CharField(source='title')

    class Meta:
        model = ClientDocument
        fields = [
            'id', 'name', 'title', 'link', 'document_type', 'document_source',
            'google_drive_id', 'category', 'visibility', 'folder', 'folder_id',
            'file_size', 'created_at', 'updated_at',
        ]

    def get_link(self, obj):
        request = self.context.get('request')
        return obj.get_document_link(request)

    def get_folder_id(self, obj):
        return obj.folder_id

    def get_file_size(self, obj):
        if obj.document:
            try:
                size = obj.document.size
                if size < 1024:
                    return f'{size} B'
                elif size < 1024 * 1024:
                    return f'{size // 1024} KB'
                else:
                    return f'{size // (1024 * 1024)} MB'
            except Exception:
                pass
        return '0 KB'


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
# Helper: get client from request user
# ---------------------------------------------------------------------------

def _get_client(user):
    """Return the Client object for this user, or None."""
    return Client.objects.filter(user=user).first()


def _is_admin(user):
    return hasattr(user, 'admin_profile')


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

        serializer = VaultFolderSerializer(folders, many=True, context={'request': request})
        return Response({"status": "success", "data": serializer.data})

    def post(self, request):
        user = request.user
        data = request.data.copy()

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
# VaultDocumentListView – GET list / POST create (file upload)
# ---------------------------------------------------------------------------

@extend_schema(tags=["vault"])
class VaultDocumentListView(APIView):
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
                return Response(
                    {"status": "error", "message": "Client profile not found."},
                    status=status.HTTP_403_FORBIDDEN
                )
            docs = ClientDocument.objects.filter(client=client, is_visible_to_client=True)

        serializer = VaultDocumentSerializer(docs, many=True, context={'request': request})
        return Response({"status": "success", "data": serializer.data})

    def post(self, request):
        user = request.user
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

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
            doc = ClientDocument.objects.get(pk=pk)
        except ClientDocument.DoesNotExist:
            return None, None

        if _is_admin(user):
            return doc, None

        client = _get_client(user)
        if not client or doc.client != client:
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
                docs = ClientDocument.objects.filter(client_id=client_id).order_by('-updated_at')[:20]
            else:
                docs = ClientDocument.objects.all().order_by('-updated_at')[:20]
        else:
            client = _get_client(user)
            if not client:
                return Response({"status": "success", "data": []})
            docs = ClientDocument.objects.filter(client=client).order_by('-updated_at')[:20]

        activities = []
        for doc in docs:
            activities.append({
                "id": doc.id,
                "user": user.get_full_name() or user.username,
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