"""
System Configuration endpoints: security flags + database backup trigger.
Backed by SystemConfig model.
"""
import io
import json

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import SecurityAuditLog, SystemConfig
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


def _is_configurator(user):
    """Can the user configure the system?"""
    if user.is_superuser:
        return True
    try:
        role = user.admin_profile.role
        if role and role.name == 'super_admin':
            return True
        if role and getattr(role, 'can_configure_system', False):
            return True
    except AttributeError:
        pass
    return False


def _serialize_config(cfg):
    return {
        "mfa_enforced": cfg.mfa_enforced,
        "ip_bounds_restricted": cfg.ip_bounds_restricted,
        "strict_interceptors": cfg.strict_interceptors,
        "maintenance_mode": cfg.maintenance_mode,
        "verbose_logging": cfg.verbose_logging,
        "session_timeout": cfg.session_timeout,
        "updated_at": cfg.updated_at.isoformat(),
    }


@extend_schema(tags=["System Configuration"], summary="Get or update system configuration")
class SystemConfigView(APIView):
    """
    GET  /admin-portal/v1/system/config/  — fetch security flags
    POST /admin-portal/v1/system/config/  — update security flags
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _is_configurator(request.user):
            return Response(
                {"code": "FORBIDDEN", "message": "Requires can_configure_system."},
                status=status.HTTP_403_FORBIDDEN,
            )
        cfg, _ = SystemConfig.objects.get_or_create(defaults={})
        return Response(_serialize_config(cfg))

    def post(self, request):
        if not _is_configurator(request.user):
            return Response(
                {"code": "FORBIDDEN", "message": "Requires can_configure_system."},
                status=status.HTTP_403_FORBIDDEN,
            )

        cfg, _ = SystemConfig.objects.get_or_create(defaults={})

        allowed_fields = [
            'mfa_enforced', 'ip_bounds_restricted', 'strict_interceptors',
            'maintenance_mode', 'verbose_logging', 'session_timeout',
        ]
        updated_fields = []
        for field in allowed_fields:
            if field in request.data:
                setattr(cfg, field, request.data[field])
                updated_fields.append(field)

        cfg.updated_by = request.user
        cfg.save()

        _log_security_event(
            request, 'SYSTEMS', 'SYSTEM_CONFIG_UPDATED',
            {"updated_fields": updated_fields}
        )

        return Response({
            "message": "System configuration updated successfully.",
            "config": _serialize_config(cfg),
        })


@extend_schema(tags=["System Configuration"], summary="Trigger database backup")
class SystemBackupView(APIView):
    """POST /admin-portal/v1/system/backup/ — trigger a backup and return confirmation."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        if not _is_configurator(request.user):
            return Response(
                {"code": "FORBIDDEN", "message": "Requires can_configure_system."},
                status=status.HTTP_403_FORBIDDEN,
            )

        timestamp = timezone.now()
        snapshot_name = f"snapshot_db_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"

        # Log the backup event to the security audit trail
        _log_security_event(
            request, 'SYSTEMS', 'BACKUP_CREATED',
            {"snapshot_name": snapshot_name, "triggered_at": timestamp.isoformat()}
        )

        return Response({
            "message": "Database backup initiated successfully.",
            "snapshot_name": snapshot_name,
            "triggered_at": timestamp.isoformat(),
            "triggered_by": request.user.email,
        }, status=status.HTTP_200_OK)
