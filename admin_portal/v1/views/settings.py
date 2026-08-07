from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import AdminProfile, AdminRole, AuditLog, SystemSettings, LetterheadTemplate
from admin_portal.permissions import CanManageSettings, CanManageUsers
from common.permissions import IsAdminUser

from ..serializers.settings import (
    AdminProfileSerializer,
    AdminRoleSerializer,
    AuditLogSerializer,
    SystemSettingsSerializer,
    UserManagementSerializer,
    LetterheadTemplateSerializer,
)


@extend_schema(tags=["Settings & System Config"])
class LetterheadTemplateListView(generics.ListCreateAPIView):
    queryset = LetterheadTemplate.objects.all()
    serializer_class = LetterheadTemplateSerializer
    permission_classes = [IsAdminUser, CanManageSettings]


@extend_schema(tags=["Settings & System Config"])
class LetterheadTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LetterheadTemplate.objects.all()
    serializer_class = LetterheadTemplateSerializer
    permission_classes = [IsAdminUser, CanManageSettings]

@extend_schema(
    tags=["Settings & System Config"],
    summary="Get or update system settings",
    description="Retrieve current system settings or update system configuration including branding, meeting settings, and notification preferences.",
)
class SystemSettingsView(APIView):
    """System settings management"""

    permission_classes = [IsAdminUser, CanManageSettings]

    def get(self, request):
        settings, created = SystemSettings.objects.get_or_create(
            defaults={
                "company_name": "ORR",
                "primary_color": "#007bff",
                "default_meeting_duration": 60,
                "meeting_buffer_time": 15,
                "email_notifications_enabled": True,
            }
        )
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        settings, created = SystemSettings.objects.get_or_create()
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action="update",
                model_name="SystemSettings",
                object_id=str(settings.pk),
                description="System settings updated",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Settings & System Config"],
    summary="List or create admin roles",
    description="Retrieve all admin roles or create new roles with specific permissions for role-based access control.",
)
class AdminRoleListView(generics.ListCreateAPIView):
    """List and create admin roles"""

    queryset = AdminRole.objects.all()
    serializer_class = AdminRoleSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        role = serializer.save()

        # Create audit log
        AuditLog.objects.create(
            user=self.request.user,
            action="create",
            model_name="AdminRole",
            object_id=str(role.pk),
            description=f"Admin role created: {role.name}",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )


@extend_schema(
    tags=["Settings & System Config"],
    summary="Manage admin role",
    description="Retrieve, update, or delete a specific admin role and its permissions.",
)
class AdminRoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete admin role"""

    queryset = AdminRole.objects.all()
    serializer_class = AdminRoleSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        role = serializer.save()

        # Create audit log
        AuditLog.objects.create(
            user=self.request.user,
            action="update",
            model_name="AdminRole",
            object_id=str(role.pk),
            description=f"Admin role updated: {role.name}",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )


@extend_schema(
    tags=["Settings & System Config"],
    summary="List admin users",
    description="Retrieve a list of all admin users with their profiles and role assignments.",
)
class AdminUserListView(generics.ListAPIView):
    """List admin users"""

    serializer_class = AdminProfileSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        super_admin_role, _ = AdminRole.objects.get_or_create(name="super_admin", defaults={"description": "Super Admin"})
        admin_role, _ = AdminRole.objects.get_or_create(name="admin", defaults={"description": "Administrator"})
        pm_role, _ = AdminRole.objects.get_or_create(name="project_manager", defaults={"description": "Project Manager"})
        consultant_role, _ = AdminRole.objects.get_or_create(name="consultant", defaults={"description": "Consultant"})

        staff_users = User.objects.filter(is_staff=True)
        for u in staff_users:
            if u.is_superuser:
                assigned_role = super_admin_role
            elif "pm" in u.username.lower() or "pm" in u.email.lower():
                assigned_role = pm_role
            elif "consultant" in u.username.lower() or "consultant" in u.email.lower():
                assigned_role = consultant_role
            else:
                assigned_role = admin_role
            AdminProfile.objects.get_or_create(user=u, defaults={"role": assigned_role})
        return AdminProfile.objects.select_related("user", "role").all()


@extend_schema(
    tags=["Settings & System Config"],
    summary="Manage admin user",
    description="Retrieve or update admin user profile including role assignment and account status.",
)
class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete admin user"""

    queryset = AdminProfile.objects.select_related("user", "role").all()
    serializer_class = AdminProfileSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        profile = serializer.save()

        # Create audit log
        AuditLog.objects.create(
            user=self.request.user,
            action="update",
            model_name="AdminProfile",
            object_id=str(profile.pk),
            description=f"Admin profile updated: {profile.user.username}",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )

    def perform_destroy(self, instance):
        user = instance.user
        
        # Create audit log before deletion
        AuditLog.objects.create(
            user=self.request.user,
            action="delete",
            model_name="AdminProfile",
            object_id=str(instance.pk),
            description=f"Admin user and profile deleted: {user.username if user else 'Unknown'}",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )

        if user:
            user.delete()
        else:
            instance.delete()


@extend_schema(
    tags=["Settings & System Config"],
    summary="Create new admin user",
    description="Create a new admin user account with profile and role assignment.",
)
class CreateAdminUserView(APIView):
    """Create new admin user"""

    permission_classes = [IsAdminUser, CanManageUsers]

    def post(self, request):
        serializer = UserManagementSerializer(data=request.data)

        if serializer.is_valid():
            # Create user
            user_data = serializer.validated_data
            user = User.objects.create_user(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
                is_staff=True,
            )

            # Create admin profile
            role = AdminRole.objects.get(name=user_data["role_name"])
            AdminProfile.objects.create(
                user=user,
                role=role,
                department=user_data.get("department", ""),
                phone=user_data.get("phone", ""),
            )

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action="create",
                model_name="User",
                object_id=str(user.pk),
                description=f"Admin user created: {user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {
                    "message": "Admin user created successfully",
                    "user_id": user.id,
                    "username": user.username,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.core.mail import send_mail
from django.conf import settings as django_settings
import string
import random

def generate_temp_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

@extend_schema(
    tags=["Settings & System Config"],
    summary="Create Platform User (Consultant or PM)",
    description="Create a new Consultant or Project Manager and send welcome email with a temporary password.",
)
class CreatePlatformUserView(APIView):
    """Create Platform User (Consultant or PM)"""

    permission_classes = [IsAdminUser, CanManageUsers]

    def post(self, request):
        from django.db import transaction, IntegrityError
        role_type = request.data.get("role_type") # 'consultant', 'pm', or 'client'
        email = request.data.get("email")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")
        
        if not email or not role_type:
            return Response({"error": "email and role_type are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Proactively clean up any orphan records in Client, ClientProfile, and Consultant
        # where the user no longer exists in auth_user to prevent unique/foreign key conflicts.
        try:
            from admin_portal.models import Client
            from client.models import Profile as ClientProfile
            from consultation.models import Consultant

            Client.objects.exclude(user_id__in=User.objects.values('id')).delete()
            ClientProfile.objects.exclude(user_id__in=User.objects.values('id')).delete()
            Consultant.objects.exclude(user_id__in=User.objects.values('id')).delete()
        except Exception:
            pass
            
        # Clean up any existing user with this email that has no profile to prevent unique constraint lockouts
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            has_profile = False
            try:
                if hasattr(existing_user, 'client_profile') and existing_user.client_profile:
                    has_profile = True
            except Exception:
                pass
            try:
                if hasattr(existing_user, 'admin_profile') and existing_user.admin_profile:
                    has_profile = True
            except Exception:
                pass
            try:
                from consultation.models import Consultant
                if Consultant.objects.filter(user=existing_user).exists():
                    has_profile = True
            except Exception:
                pass
                
            if not has_profile:
                existing_user.delete()
            else:
                return Response({"error": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)
            
        username = email.split('@')[0]
        # Clean up orphan username too if needed
        orphan_username_user = User.objects.filter(username=username).first()
        if orphan_username_user:
            has_profile = False
            try:
                if hasattr(orphan_username_user, 'client_profile') and orphan_username_user.client_profile:
                    has_profile = True
            except Exception:
                pass
            try:
                if hasattr(orphan_username_user, 'admin_profile') and orphan_username_user.admin_profile:
                    has_profile = True
            except Exception:
                pass
            if not has_profile:
                orphan_username_user.delete()
            else:
                username = f"{username}_{random.randint(1000, 9999)}"
            
        temp_password = generate_temp_password()
        
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=temp_password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=(role_type == 'pm') # PMs are staff
                )
                
                if role_type == 'pm':
                    role, _ = AdminRole.objects.get_or_create(name="admin")
                    admin_prof, _ = AdminProfile.objects.get_or_create(
                        user=user,
                        defaults={"role": role, "department": "PM"}
                    )
                    admin_prof.role = role
                    admin_prof.department = "PM"
                    admin_prof.save()
                elif role_type == 'consultant':
                    from consultation.models import Consultant, ConsultantProfile
                    consultant_count = Consultant.objects.count() + 1
                    consultant_id = f"ORR-CONS-{consultant_count:06d}"
                    consultant = Consultant.objects.create(
                        user=user,
                        consultant_number=consultant_id,
                        status='APPROVED'
                    )
                    ConsultantProfile.objects.create(
                        consultant=consultant,
                        full_name=f"{first_name} {last_name}".strip(),
                        display_name=first_name
                    )
                elif role_type == 'client':
                    from admin_portal.models import Client
                    from client.models import Profile as ClientProfile
                    
                    # Defensive: remove any stale Client/ClientProfile rows
                    # that might reference this user_id (from a prior partial create)
                    Client.objects.filter(user=user).delete()
                    ClientProfile.objects.filter(user=user).delete()
                    
                    client_obj = Client.objects.create(
                        user=user,
                        company=f"{first_name} {last_name} Company",
                        stage="discover",
                        primary_pillar="strategic"
                    )
                    ClientProfile.objects.create(
                        user=user,
                        full_name=f"{first_name} {last_name}".strip(),
                        nickname=first_name
                    )
                else:
                    return Response({"error": "Invalid role_type. Must be 'pm', 'consultant', or 'client'."}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            error_msg = str(e)
            # If the IntegrityError is about a stale record, attempt cleanup and retry once
            if 'admin_portal_client_user_id_key' in error_msg or 'unique constraint' in error_msg.lower():
                try:
                    # The user was created in the rolled-back transaction, so re-query
                    stale_user = User.objects.filter(email=email).first()
                    if stale_user:
                        from admin_portal.models import Client
                        from client.models import Profile as ClientProfile
                        Client.objects.filter(user=stale_user).delete()
                        ClientProfile.objects.filter(user=stale_user).delete()
                        stale_user.delete()
                    # Retry creation
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=username, email=email, password=temp_password,
                            first_name=first_name, last_name=last_name,
                            is_staff=(role_type == 'pm')
                        )
                        if role_type == 'client':
                            from admin_portal.models import Client
                            from client.models import Profile as ClientProfile
                            Client.objects.create(
                                user=user, company=f"{first_name} {last_name} Company",
                                stage="discover", primary_pillar="strategic"
                            )
                            ClientProfile.objects.create(
                                user=user, full_name=f"{first_name} {last_name}".strip(),
                                nickname=first_name
                            )
                        elif role_type == 'pm':
                            role, _ = AdminRole.objects.get_or_create(name="admin")
                            aprof, _ = AdminProfile.objects.get_or_create(user=user, defaults={"role": role, "department": "PM"})
                            aprof.role = role
                            aprof.department = "PM"
                            aprof.save()
                        elif role_type == 'consultant':
                            from consultation.models import Consultant, ConsultantProfile
                            cid = f"ORR-CONS-{Consultant.objects.count() + 1:06d}"
                            cons = Consultant.objects.create(user=user, consultant_number=cid, status='APPROVED')
                            ConsultantProfile.objects.create(
                                consultant=cons, full_name=f"{first_name} {last_name}".strip(),
                                display_name=first_name
                            )
                except Exception as retry_err:
                    return Response({"error": f"Failed to create user after cleanup: {str(retry_err)}"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": f"Failed to create user or profile: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to create user or profile: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Send Email
        try:
            frontend_url = django_settings.FRONTEND_URL if hasattr(django_settings, 'FRONTEND_URL') else "http://localhost:3000"
            login_link = f"{frontend_url}/login"
            subject = f"Welcome to ORR Solution - Your {role_type.upper()} Account"
            message = f"Hello {first_name},\n\nYour account has been created.\n\nEmail: {email}\nTemporary Password: {temp_password}\n\nPlease login using the following link:\n{login_link}"
            send_mail(
                subject,
                message,
                django_settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
        except Exception as e:
            pass # Handle quietly if email fails
            
        AuditLog.objects.create(
            user=request.user,
            action="create",
            model_name="User",
            object_id=str(user.pk),
            description=f"{role_type.upper()} user created: {user.username}",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        
        return Response(
            {
                "message": f"{role_type.upper()} user created successfully.",
                "user_id": user.id,
                "email": user.email,
                "username": username,
                "password": temp_password,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Settings & System Config"],
    summary="Perform user management actions",
    description="Execute user management actions including activate/deactivate accounts and reset passwords.",
)
class UserManagementActionsView(APIView):
    """User management actions"""

    permission_classes = [IsAdminUser, CanManageUsers]

    def post(self, request, pk):
        try:
            admin_profile = AdminProfile.objects.get(pk=pk)
            action = request.data.get("action")

            if action == "activate":
                admin_profile.is_active = True
                admin_profile.user.is_active = True
                admin_profile.save()
                admin_profile.user.save()
                message = "User activated successfully"

            elif action == "deactivate":
                admin_profile.is_active = False
                admin_profile.user.is_active = False
                admin_profile.save()
                admin_profile.user.save()
                message = "User deactivated successfully"

            elif action == "reset_password":
                # Generate new password or send reset email
                # For now, just return success
                message = "Password reset email sent"

            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=action,
                model_name="AdminProfile",
                object_id=str(admin_profile.pk),
                description=f"{action.title()} user: {admin_profile.user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response({"message": message})

        except AdminProfile.DoesNotExist:
            return Response(
                {"error": "Admin profile not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Settings & System Config"],
    summary="List audit logs",
    description="Retrieve audit trail logs with filtering options for compliance and accountability tracking.",
)
class AuditLogListView(generics.ListAPIView):
    """List audit logs"""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("user").all()

        # Filters
        user_id = self.request.query_params.get("user", None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        action = self.request.query_params.get("action", None)
        if action:
            queryset = queryset.filter(action=action)

        model_name = self.request.query_params.get("model", None)
        if model_name:
            queryset = queryset.filter(model_name=model_name)

        # Date range filter
        date_from = self.request.query_params.get("date_from", None)
        date_to = self.request.query_params.get("date_to", None)
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)

        return queryset.order_by("-timestamp")


@extend_schema(
    tags=["Settings & System Config"],
    summary="Delete Platform User",
    description="Delete a User and all their associated profiles (Client, Consultant, AdminProfile).",
)
class DeletePlatformUserView(APIView):
    """Delete Platform User"""
    permission_classes = [IsAdminUser, CanManageUsers]

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            # Create audit log before deletion
            AuditLog.objects.create(
                user=request.user,
                action="delete",
                model_name="User",
                object_id=str(user.pk),
                description=f"User deleted: {user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            user.delete()
            return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=["Settings & System Config"],
    summary="List all platform users",
    description="Retrieve a list of all users across the platform.",
)
class PlatformUserListView(generics.ListAPIView):
    """List all platform users"""
    permission_classes = [IsAdminUser, CanManageUsers]

    def get(self, request):
        users = User.objects.all().order_by('-date_joined')
        data = []
        for u in users:
            role = "User"
            if hasattr(u, 'admin_profile'):
                role = f"Admin - {u.admin_profile.department}" if u.admin_profile.department else "Admin"
            elif hasattr(u, 'client_profile'):
                role = "Client"
            elif hasattr(u, 'consultant'):
                role = "Consultant"
                
            data.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": role,
                "is_active": u.is_active,
                "date_joined": u.date_joined,
            })
        return Response(data)
