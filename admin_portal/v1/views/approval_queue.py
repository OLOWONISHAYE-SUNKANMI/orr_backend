"""
Dual-Approval Queue endpoints.
Sensitive admin actions are intercepted and placed in ApprovalQueue;
only super_admins with can_approve_sensitive_actions may decide them.
"""
import uuid

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import ApprovalQueue, SecurityAuditLog
from admin_portal.permissions import IsAdminUser


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _log_security_event(request, category, event_name, metadata=None):
    user = request.user
    try:
        SecurityAuditLog.objects.create(
            event_category=category,
            event_name=event_name,
            user_id=str(user.id),
            user_email=user.email,
            ip_address=_get_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata=metadata or {},
        )
    except Exception:
        pass


def _is_approver(user):
    """Check if user can approve sensitive actions."""
    if user.is_superuser:
        return True
    try:
        role = user.admin_profile.role
        if role and role.name == 'super_admin':
            return True
        if role and getattr(role, 'can_approve_sensitive_actions', False):
            return True
    except AttributeError:
        pass
    return False


def _serialize_queue_item(item):
    return {
        "id": item.id,
        "action_type": item.action_type,
        "requested_by": item.requested_by,
        "requested_by_name": item.requested_by_name,
        "requested_by_role": item.requested_by_role,
        "requested_at": item.requested_at.isoformat(),
        "payload": item.payload,
        "status": item.status,
        "decided_by": item.decided_by,
        "decided_by_name": item.decided_by_name,
        "decided_at": item.decided_at.isoformat() if item.decided_at else None,
        "rejection_reason": item.rejection_reason,
    }


@extend_schema(tags=["Approval Queue"], summary="List approval queue items")
class ApprovalQueueListView(APIView):
    """
    GET  /admin-portal/v1/approvals/queue/          – list items (filter ?status=PENDING|APPROVED|REJECTED)
    POST /admin-portal/v1/approvals/queue/          – create a new pending approval request
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _is_approver(request.user):
            return Response(
                {"code": "FORBIDDEN", "message": "Requires can_approve_sensitive_actions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = ApprovalQueue.objects.all()
        filter_status = request.query_params.get('status')
        if filter_status and filter_status.upper() in ('PENDING', 'APPROVED', 'REJECTED'):
            qs = qs.filter(status=filter_status.upper())

        search = request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(id__icontains=search) |
                Q(action_type__icontains=search) |
                Q(requested_by_name__icontains=search)
            )

        data = [_serialize_queue_item(item) for item in qs]
        return Response({"results": data, "count": len(data)})

    def post(self, request):
        """Any admin can submit a sensitive action request — backend auto-intercepts it."""
        user = request.user
        action_type = request.data.get('action_type', '')
        payload = request.data.get('payload', {})

        if not action_type:
            return Response(
                {"error": "action_type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        # Determine requester role name
        role_name = 'unknown'
        try:
            if user.admin_profile and user.admin_profile.role:
                role_name = user.admin_profile.role.name
        except AttributeError:
            pass

        item = ApprovalQueue.objects.create(
            id=req_id,
            action_type=action_type,
            requested_by=str(user.id),
            requested_by_name=user.get_full_name() or user.username,
            requested_by_role=role_name,
            payload=payload,
            status='PENDING',
        )

        _log_security_event(
            request, 'DUAL_APPROVALS', 'APPROVAL_REQUEST_SUBMITTED',
            {"request_id": req_id, "action_type": action_type}
        )

        # Trigger 36-admin-approval-request
        try:
            from django.contrib.auth.models import User
            from admin_portal.orr_email_service import ORREmailService
            import datetime
            # Find super admins or users with can_approve_sensitive_actions
            approvers = User.objects.filter(is_staff=True, admin_profile__role__can_approve_sensitive_actions=True)
            superadmins = User.objects.filter(is_superuser=True)
            approver_emails = list(set(list(approvers.values_list('email', flat=True)) + list(superadmins.values_list('email', flat=True))))
            
            if approver_emails:
                ORREmailService.send_admin_approval_request(
                    recipient_emails=approver_emails,
                    requester_name=user.get_full_name() or user.username,
                    action_type=action_type,
                    request_id=req_id,
                    request_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    review_url=f"https://orr.solutions/admin/approvals/{req_id}"
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send approval request email: {e}")

        return Response(
            {
                "message": "Sensitive action intercepted. Submitted for Super Admin review.",
                "request_id": req_id,
                "status": "PENDING",
            },
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=["Approval Queue"], summary="Decide on an approval request")
class ApprovalQueueDecideView(APIView):
    """POST /admin-portal/v1/approvals/queue/:id/decide/"""

    permission_classes = [IsAdminUser]

    def post(self, request, req_id):
        if not _is_approver(request.user):
            return Response(
                {"code": "FORBIDDEN", "message": "Requires can_approve_sensitive_actions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        decision = request.data.get('decision', '').upper()
        reason = request.data.get('reason', '')

        if decision not in ('APPROVED', 'REJECTED'):
            return Response(
                {"error": "decision must be APPROVED or REJECTED."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if decision == 'REJECTED' and not reason.strip():
            return Response(
                {"error": "A rejection reason is required when decision is REJECTED."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import transaction
        try:
            with transaction.atomic():
                item = ApprovalQueue.objects.select_for_update().get(id=req_id, status='PENDING')
                user = request.user
                item.status = decision
                item.decided_by = str(user.id)
                item.decided_by_name = user.get_full_name() or user.username
                item.decided_at = timezone.now()
                item.rejection_reason = reason if decision == 'REJECTED' else ''
                item.save()
        except ApprovalQueue.DoesNotExist:
            return Response(
                {"error": "Approval request not found or already decided."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Log to security audit trail
        event_name = 'ACTION_APPROVED' if decision == 'APPROVED' else 'ACTION_REJECTED'
        _log_security_event(
            request, 'DUAL_APPROVALS', event_name,
            {
                "request_id": req_id,
                "action_type": item.action_type,
                "decision": decision,
                "reason": reason,
            }
        )

        # Trigger 37-admin-approval-status
        try:
            from django.contrib.auth.models import User
            from admin_portal.orr_email_service import ORREmailService
            requester = User.objects.filter(id=item.requested_by).first()
            if requester and requester.email:
                ORREmailService.send_admin_approval_status(
                    recipient_email=requester.email,
                    request_id=item.id,
                    action_type=item.action_type,
                    status=decision,
                    approver_name=user.get_full_name() or user.username,
                    approval_notes=reason or "Reviewed by admin."
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send approval status email: {e}")

        return Response({
            "message": f"Request {req_id} has been {decision.lower()}.",
            "item": _serialize_queue_item(item),
        })
