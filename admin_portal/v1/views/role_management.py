from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import AdminProfile, AdminRole, AuditLog
from admin_portal.permissions import CanManageSettings

from ..serializers.settings import AdminRoleSerializer


@extend_schema(
    tags=["Role Management"],
    summary="Update role permissions",
    description="Super Admin can update permissions for any role.",
)
class UpdateRolePermissionsView(APIView):
    """Super Admin can update role permissions"""

    permission_classes = [CanManageSettings]

    def put(self, request, role_id):
        try:
            role = AdminRole.objects.get(id=role_id)

            # Update permissions
            permissions = request.data.get("permissions", {})
            for perm, value in permissions.items():
                if hasattr(role, perm):
                    setattr(role, perm, value)

            role.save()

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action="update",
                model_name="AdminRole",
                object_id=str(role.id),
                description=f"Updated permissions for role: {role.name}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {
                    "message": "Role permissions updated successfully",
                    "role": AdminRoleSerializer(role).data,
                }
            )

        except AdminRole.DoesNotExist:
            return Response(
                {"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Role Management"],
    summary="Deactivate user",
    description="Super Admin can deactivate any user.",
)
class DeactivateUserView(APIView):
    """Super Admin can deactivate users"""

    permission_classes = [CanManageSettings]

    def post(self, request, user_id):
        try:
            admin_profile = AdminProfile.objects.get(user_id=user_id)

            # Deactivate user
            admin_profile.is_active = False
            admin_profile.user.is_active = False
            admin_profile.save()
            admin_profile.user.save()

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action="deactivate",
                model_name="User",
                object_id=str(user_id),
                description=f"Deactivated user: {admin_profile.user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            if admin_profile.user.email:
                try:
                    from admin_portal.orr_email_service import ORREmailService
                    ORREmailService.send_access_revoked(
                        recipient_email=admin_profile.user.email,
                        workspace_name="ORR Solutions Admin Portal",
                        revocation_reason="Your account has been deactivated by an administrator.",
                        revocation_date=admin_profile.updated_at.strftime("%Y-%m-%d %H:%M") if hasattr(admin_profile, 'updated_at') else "Immediate"
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to send access revoked notification: {e}")

            return Response({"message": "User deactivated successfully"})

        except AdminProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Role Management"],
    summary="Edit any user",
    description="Super Admin can edit any user's profile and role.",
)
class EditUserView(APIView):
    """Super Admin can edit any user"""

    permission_classes = [CanManageSettings]

    def put(self, request, user_id):
        try:
            admin_profile = AdminProfile.objects.get(user_id=user_id)
            user = admin_profile.user

            # Update user fields
            user_data = request.data.get("user", {})
            if "first_name" in user_data:
                user.first_name = user_data["first_name"]
            if "last_name" in user_data:
                user.last_name = user_data["last_name"]
            if "email" in user_data:
                user.email = user_data["email"]
            if "is_active" in user_data:
                user.is_active = user_data["is_active"]
            user.save()

            # Update profile fields
            profile_data = request.data.get("profile", {})
            role_changed = False
            new_role_name = None
            if "role_name" in profile_data:
                role = AdminRole.objects.get(name=profile_data["role_name"])
                if admin_profile.role != role:
                    role_changed = True
                    new_role_name = role.name
                admin_profile.role = role
            if "department" in profile_data:
                admin_profile.department = profile_data["department"]
            if "phone" in profile_data:
                admin_profile.phone = profile_data["phone"]
            admin_profile.save()

            if role_changed and user.email:
                try:
                    from admin_portal.orr_email_service import ORREmailService
                    ORREmailService.send_role_change_notification(
                        recipient_email=user.email,
                        workspace_name="ORR Solutions Portal",
                        new_role_name=new_role_name,
                        role_description=role.description if hasattr(role, 'description') else "Role updated by admin.",
                        dashboard_url="https://orr.solutions/admin/dashboard"
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to send role change notification: {e}")

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action="update",
                model_name="User",
                object_id=str(user_id),
                description=f"Edited user: {user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {
                    "message": "User updated successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_active": user.is_active,
                        "role": admin_profile.role.name if admin_profile.role else None,
                        "department": admin_profile.department,
                    },
                }
            )

        except AdminProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except AdminRole.DoesNotExist:
            return Response(
                {"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST
            )
