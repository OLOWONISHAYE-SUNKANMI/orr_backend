import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Q
from consultation.models import Consultant
from admin_portal.v1.serializers.consultant_serializers import PendingConsultantSerializer
from admin_portal.permissions import IsAdminUser
from pm.models import PMConsultantMatch, PMProject

logger = logging.getLogger(__name__)

class ConsultantDirectorySerializer(PendingConsultantSerializer):
    """Reuse the pending consultant serializer for directory since fields are identical"""
    pass

@extend_schema(tags=["Consultant Directory"])
class ConsultantDirectoryListView(APIView):
    """
    List all APPROVED consultants for the Consultant Directory.
    Supports filtering by skill, specialization, name, or location.
    """
    permission_classes = [IsAdminUser]
    
    @extend_schema(
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, description='Search by name, email, or skill'),
            OpenApiParameter('rating', OpenApiTypes.STR, description='Filter by internal rating (HIGH, MEDIUM, LOW)'),
        ],
        responses=ConsultantDirectorySerializer(many=True)
    )
    def get(self, request):
        # Only show approved consultants in the directory
        queryset = Consultant.objects.filter(status='APPROVED').select_related(
            'user', 'profile', 'specialization', 'it_competence', 
            'experience', 'work_preference', 'commercials', 'compliance'
        ).prefetch_related('skills')

        search_query = request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(skills__name__icontains=search_query) |
                Q(specialization__primary_specialization__icontains=search_query)
            ).distinct()

        rating_query = request.query_params.get('rating', None)
        if rating_query:
            queryset = queryset.filter(internal_rating=rating_query.upper())

        serializer = ConsultantDirectorySerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Consultant Directory"])
class ConsultantDirectoryDetailView(APIView):
    """Details of a specific approved consultant"""
    permission_classes = [IsAdminUser]

    @extend_schema(responses=ConsultantDirectorySerializer)
    def get(self, request, pk):
        try:
            consultant = Consultant.objects.get(pk=pk, status='APPROVED')
            serializer = ConsultantDirectorySerializer(consultant)
            return Response(serializer.data)
        except Consultant.DoesNotExist:
            return Response({"error": "Consultant not found"}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(tags=["Consultant Directory"])
class ConsultantSourcingProtocolView(APIView):
    """
    Assign a consultant to a project using the sourcing protocol.
    Creates a PMConsultantMatch.
    """
    permission_classes = [IsAdminUser]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "consultant_id": {"type": "integer"},
                    "match_label": {"type": "string", "enum": ['strong_match', 'good_match', 'partial_match', 'manual_review']},
                    "match_reason": {"type": "string"}
                },
                "required": ["project_id", "consultant_id"]
            }
        }
    )
    def post(self, request):
        project_id = request.data.get('project_id')
        consultant_id = request.data.get('consultant_id')
        match_label = request.data.get('match_label', 'manual_review')
        match_reason = request.data.get('match_reason', 'Assigned via admin directory')

        try:
            project = PMProject.objects.get(id=project_id)
            consultant = Consultant.objects.get(id=consultant_id, status='APPROVED')

            # Create the match
            match, created = PMConsultantMatch.objects.update_or_create(
                project=project,
                consultant=consultant,
                defaults={
                    'match_label': match_label,
                    'match_reason': match_reason
                }
            )

            # Update project status if needed
            if project.stage in ['approved_for_sourcing', 'ready_for_matching']:
                project.stage = 'consultant_assignment_pending'
                project.save(update_fields=['stage', 'updated_at'])

            return Response({
                "status": "success",
                "message": f"Consultant assigned to project successfully",
                "match_id": match.id
            })

        except PMProject.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        except Consultant.DoesNotExist:
            return Response({"error": "Consultant not found or not approved"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error matching consultant: {str(e)}")
            return Response(
                {"success": False, "error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConsultantJobAssignView(APIView):
    """
    Admin explicitly assigns a requested consultant to a project.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, job_id):
        from consultation.models import ConsultantJob, Consultant
        from common.response import api_response

        try:
            job = ConsultantJob.objects.get(id=job_id)
        except ConsultantJob.DoesNotExist:
            return Response(api_response(success=False, error="Job not found", status_code=status.HTTP_404_NOT_FOUND))
        
        consultant_id = request.data.get("consultant_id")
        if not consultant_id:
            return Response(api_response(success=False, error="consultant_id is required", status_code=status.HTTP_400_BAD_REQUEST))

        try:
            consultant = Consultant.objects.get(id=consultant_id)
        except Consultant.DoesNotExist:
            return Response(api_response(success=False, error="Consultant not found", status_code=status.HTTP_404_NOT_FOUND))

        job.consultant = consultant
        job.status = 'ASSIGNED_BY_ADMIN'
        job.save()

        # TODO: Trigger notification to Consultant here if notification system is active.

        return Response(api_response(
            success=True,
            message=f"Consultant {consultant.user.email if consultant.user else 'Unknown'} assigned to job {job.title}."
        ))
