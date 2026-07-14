from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from consultation.models import Consultant
from ..serializers.consultant_serializers import PendingConsultantSerializer
from common.response import api_response

class ConsultantApprovalsListView(APIView):
    """
    List all pending consultant profile requests.
    """
    permission_classes = [IsAuthenticated] # Or IsSuperAdminOrAdmin depending on setup

    def get(self, request):
        # Fetch consultants who have finished onboarding and are pending review
        pending_consultants = Consultant.objects.filter(status='PENDING_REVIEW').order_by('-created_at')
        serializer = PendingConsultantSerializer(pending_consultants, many=True)
        return Response(api_response(
            success=True,
            data=serializer.data,
            message="Successfully retrieved pending consultant approvals."
        ))

class ConsultantApprovalActionView(APIView):
    """
    Approve or reject a consultant profile request.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            consultant = Consultant.objects.get(pk=pk, status='PENDING_REVIEW')
        except Consultant.DoesNotExist:
            return Response(api_response(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Consultant application not found or is no longer pending."
            ))

        action = request.data.get('action')
        admin_notes = request.data.get('notes', '')

        if action not in ['approve', 'reject']:
            return Response(api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid action. Must be 'approve' or 'reject'."
            ))

        consultant.approved_by = request.user
        consultant.approval_date = timezone.now()
        
        if admin_notes:
            consultant.admin_notes = admin_notes

        if action == 'approve':
            consultant.status = 'APPROVED'
            # Grant access to consultant portal by setting is_staff to True
            user = consultant.user
            user.is_staff = True
            user.save()
            message = "Consultant application approved successfully."
        else:
            consultant.status = 'REJECTED'
            message = "Consultant application rejected."

        consultant.save()

        return Response(api_response(
            success=True,
            data={"status": consultant.status},
            message=message
        ))
