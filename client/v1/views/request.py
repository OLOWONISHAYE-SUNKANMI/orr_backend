"""
Views for Client Problem / Request Brief Form.
Implements the client-facing CRUD operations, submission,
admin review, PM assignment, and project conversion endpoints.
"""

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from client.models import ClientRequest, ClientRequestDocument, ClientRequestVersion
from client.v1.serializers.request_serializer import (
    ClientRequestSerializer,
    ClientRequestListSerializer,
    ClientRequestDocumentSerializer,
    ClientRequestVersionSerializer,
    ClientRequestAdminReviewSerializer,
    ClientRequestConvertToProjectSerializer,
)


def _generate_request_id():
    """Generate unique request reference: ORR-REQ-000001"""
    last = ClientRequest.objects.order_by('-id').first()
    next_num = (last.id + 1) if last else 1
    return f"ORR-REQ-{next_num:06d}"


def _track_version(request_obj, user, field_name, old_val, new_val, reason=''):
    """Create a version history entry for a field change."""
    last_version = request_obj.versions.order_by('-version_number').first()
    next_version = (last_version.version_number + 1) if last_version else 1

    ClientRequestVersion.objects.create(
        request=request_obj,
        version_number=next_version,
        changed_by=user,
        field_changed=field_name,
        old_value=str(old_val) if old_val else '',
        new_value=str(new_val) if new_val else '',
        change_reason=reason,
    )


# ═══════════════════════════════════════════════════════════
# CLIENT-FACING ENDPOINTS
# ═══════════════════════════════════════════════════════════

class ClientRequestListCreateView(generics.ListCreateAPIView):
    """
    GET:  List all requests for the authenticated client.
    POST: Create a new request (saved as draft by default).
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ClientRequestListSerializer
        return ClientRequestSerializer

    def get_queryset(self):
        user = self.request.user
        return ClientRequest.objects.filter(submitted_by=user).select_related(
            'client', 'submitted_by', 'assigned_pm'
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        # Auto-generate request_id
        if not instance.request_id:
            instance.request_id = _generate_request_id()
            instance.save(update_fields=['request_id'])


class ClientRequestDetailView(generics.RetrieveUpdateAPIView):
    """
    GET:   Retrieve a single request by ID.
    PATCH: Update a request (only if status is 'draft' or 'clarification_requested').
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClientRequestSerializer

    def get_queryset(self):
        user = self.request.user
        return ClientRequest.objects.filter(submitted_by=user).select_related(
            'client', 'submitted_by', 'assigned_pm'
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.status not in ('draft', 'clarification_requested'):
            raise serializers.ValidationError(
                {"status": "Cannot edit a request that has already been submitted and is under review."}
            )

        # Track changes for audit trail
        tracked_fields = [
            'request_title', 'short_description', 'desired_outcome',
            'sensitivity_level', 'urgency', 'status', 'orr_service_area',
        ]
        for field in tracked_fields:
            if field in serializer.validated_data:
                old_val = getattr(instance, field)
                new_val = serializer.validated_data[field]
                if str(old_val) != str(new_val):
                    _track_version(instance, self.request.user, field, old_val, new_val)

        serializer.save()


class ClientRequestSubmitView(APIView):
    """
    POST: Submit a draft request.
    Changes status from 'draft' to 'submitted' → 'pending_orr_review'.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            client_request = ClientRequest.objects.get(
                pk=pk, submitted_by=request.user
            )
        except ClientRequest.DoesNotExist:
            return Response(
                {"message": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if client_request.status not in ('draft', 'clarification_requested'):
            return Response(
                {"message": "This request has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate required fields for submission
        if not client_request.confirm_accuracy:
            return Response(
                {"message": "You must confirm the accuracy of the information before submitting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not client_request.confidentiality_agreed:
            return Response(
                {"message": "You must agree to the confidentiality notice before submitting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = client_request.status
        client_request.status = 'submitted'
        client_request.submission_date = timezone.now()
        client_request.last_updated_by = request.user
        client_request.save(update_fields=['status', 'submission_date', 'last_updated_by', 'updated_at'])

        _track_version(client_request, request.user, 'status', old_status, 'submitted', 'Client submitted request')

        serializer = ClientRequestSerializer(client_request, context={'request': request})
        return Response(
            {"message": "Request submitted successfully.", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class ClientRequestDocumentUploadView(APIView):
    """
    POST: Upload documents to a request.
    GET:  List documents for a request.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        try:
            client_request = ClientRequest.objects.get(
                pk=pk, submitted_by=request.user
            )
        except ClientRequest.DoesNotExist:
            return Response(
                {"message": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        documents = client_request.documents.all()
        serializer = ClientRequestDocumentSerializer(documents, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, pk):
        try:
            client_request = ClientRequest.objects.get(
                pk=pk, submitted_by=request.user
            )
        except ClientRequest.DoesNotExist:
            return Response(
                {"message": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        files = request.FILES.getlist('files')
        descriptions = request.data.getlist('descriptions', [])

        if not files:
            return Response(
                {"message": "No files provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_docs = []
        for i, file in enumerate(files):
            desc = descriptions[i] if i < len(descriptions) else ''
            doc = ClientRequestDocument.objects.create(
                request=client_request,
                file=file,
                description=desc,
                uploaded_by=request.user,
            )
            created_docs.append(doc)

        # Update has_documents flag
        if not client_request.has_documents:
            client_request.has_documents = True
            client_request.save(update_fields=['has_documents'])

        serializer = ClientRequestDocumentSerializer(created_docs, many=True)
        return Response(
            {"message": f"{len(created_docs)} document(s) uploaded.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class ClientRequestVersionsView(generics.ListAPIView):
    """
    GET: List version history / audit trail for a request.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClientRequestVersionSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return ClientRequestVersion.objects.filter(
            request__pk=pk,
            request__submitted_by=self.request.user,
        ).select_related('changed_by')


# ═══════════════════════════════════════════════════════════
# ADMIN / INTERNAL ENDPOINTS
# ═══════════════════════════════════════════════════════════

class ClientRequestAdminCreateView(generics.CreateAPIView):
    """
    POST: Admin creates a request internally on behalf of a client.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClientRequestSerializer

    def perform_create(self, serializer):
        instance = serializer.save(
            source="internally_sourced",
            status="submitted",
            submission_date=timezone.now(),
            submitted_by=self.request.user
        )
        if not instance.request_id:
            instance.request_id = _generate_request_id()
            instance.save(update_fields=['request_id'])


class ClientRequestAdminListView(generics.ListAPIView):
    """
    GET: List all requests for admin review.
    Supports filtering by status.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClientRequestListSerializer

    def get_queryset(self):
        qs = ClientRequest.objects.exclude(status='draft').select_related(
            'client', 'submitted_by', 'assigned_pm'
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class ClientRequestAdminDetailView(generics.RetrieveAPIView):
    """
    GET: Admin view of a request with full details including internal fields.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClientRequestSerializer

    def get_queryset(self):
        return ClientRequest.objects.select_related(
            'client', 'submitted_by', 'assigned_pm'
        )


class ClientRequestAdminReviewView(APIView):
    """
    POST: Admin reviews a request.
    Actions: approve_for_meeting, approve_for_pm_assignment,
             request_clarification, reject, close, archive.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            client_request = ClientRequest.objects.get(pk=pk)
        except ClientRequest.DoesNotExist:
            return Response(
                {"message": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientRequestAdminReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        old_status = client_request.status

        # Map action to new status
        status_map = {
            'approve_for_meeting': 'approved_for_meeting',
            'approve_for_pm_assignment': 'approved_for_pm_assignment',
            'request_clarification': 'clarification_requested',
            'reject': 'rejected',
            'close': 'closed',
            'archive': 'archived',
        }

        new_status = status_map.get(action)
        if new_status:
            client_request.status = new_status

        # Update admin fields
        if 'admin_classification' in serializer.validated_data:
            client_request.admin_classification = serializer.validated_data['admin_classification']
        if 'admin_review_notes' in serializer.validated_data:
            client_request.admin_review_notes = serializer.validated_data['admin_review_notes']

        # Handle PM assignment
        if action == 'approve_for_pm_assignment':
            pm_id = serializer.validated_data.get('assigned_pm_id')
            try:
                pm_user = User.objects.get(pk=pm_id)
                client_request.assigned_pm = pm_user
            except User.DoesNotExist:
                return Response(
                    {"message": "PM user not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        client_request.last_updated_by = request.user
        client_request.save()

        _track_version(
            client_request, request.user, 'status',
            old_status, new_status,
            f"Admin review: {action}"
        )

        result_serializer = ClientRequestSerializer(
            client_request, context={'request': request}
        )
        return Response(
            {"message": f"Request {action.replace('_', ' ')}.", "data": result_serializer.data},
            status=status.HTTP_200_OK,
        )


class ClientRequestConvertToProjectView(APIView):
    """
    POST: Convert an approved request into a PM Project.
    Links the request to the new project via converted_project FK.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            client_request = ClientRequest.objects.get(pk=pk)
        except ClientRequest.DoesNotExist:
            return Response(
                {"message": "Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if client_request.status not in ('approved_for_pm_assignment', 'approved_for_meeting'):
            return Response(
                {"message": "Only approved requests can be converted to projects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClientRequestConvertToProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from pm.models import PMProject

        # Auto-generate project ID
        last_project = PMProject.objects.order_by('-id').first()
        next_num = (last_project.id + 1) if last_project else 1
        project_id = f"ORR-PROJ-{next_num:06d}"

        # Create the project from request data
        project = PMProject.objects.create(
            project_id=project_id,
            client=client_request.client,
            assigned_pm=client_request.assigned_pm,
            title=serializer.validated_data['project_title'],
            service_category=serializer.validated_data['service_category'],
            client_objective=client_request.desired_outcome,
            main_problem=client_request.short_description,
            urgency=client_request.urgency,
            confidentiality_level=client_request.sensitivity_level,
            status='draft',
        )

        # Link the request to the project
        old_status = client_request.status
        client_request.converted_project = project
        client_request.status = 'converted_to_project'
        client_request.last_updated_by = request.user
        client_request.save(update_fields=[
            'converted_project', 'status', 'last_updated_by', 'updated_at'
        ])

        _track_version(
            client_request, request.user, 'status',
            old_status, 'converted_to_project',
            f"Converted to project {project_id}"
        )

        return Response(
            {
                "message": f"Request converted to project {project_id}.",
                "data": {
                    "request_id": client_request.request_id,
                    "project_id": project_id,
                    "project_pk": project.pk,
                }
            },
            status=status.HTTP_201_CREATED,
        )

from django.contrib.auth import get_user_model

class ClientRequestAdminPMListView(APIView):
    """
    GET: Returns a list of available Project Managers for assignment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        User = get_user_model()
        # For prototype, all staff/admins can act as PMs
        pms = User.objects.filter(is_staff=True)
        data = [
            {
                "id": pm.id,
                "name": f"{pm.get_full_name() or pm.username or 'Project Manager'} ({pm.email})",
                "email": pm.email
            } for pm in pms
        ]
        return Response(data, status=status.HTTP_200_OK)
