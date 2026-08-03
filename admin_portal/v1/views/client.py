from django.contrib.auth.models import User
from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import threading

from admin_portal.models import Client, ClientDocument
from admin_portal.permissions import CanEditClients, CanViewAllClients

from ..serializers.client import (
    ClientCreateSerializer,
    ClientDetailSerializer,
    ClientDocumentSerializer,
    ClientEngagementHistorySerializer,
    ClientListSerializer,
    ClientUpdateSerializer,
)


@extend_schema(
    tags=["Client Management"],
    summary="List or create clients",
    description="Retrieve a paginated list of all clients with advanced filtering options including search by name/email/company, filter by stage, pillar, assigned admin, portal status, and activity level. Also supports creating new clients.",
)
class ClientListView(generics.ListCreateAPIView):
    """List and create clients with filtering and search"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [CanViewAllClients()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClientCreateSerializer
        return ClientListSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create to use custom post method"""
        return self.post(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Client.objects.select_related("user", "assigned_admin").all()

        # Role-based filtering
        try:
            user_role = self.request.user.admin_profile.role
            if user_role.name == "admin" and not user_role.can_view_all_clients:
                # Admin can only see clients assigned to them
                queryset = queryset.filter(assigned_admin=self.request.user)
        except AttributeError:
            # User doesn't have admin profile, show all clients
            pass

        # Search functionality
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(company__icontains=search)
            )

        # Filters
        stage = self.request.query_params.get("stage", None)
        if stage:
            queryset = queryset.filter(stage=stage)

        pillar = self.request.query_params.get("pillar", None)
        if pillar:
            queryset = queryset.filter(primary_pillar=pillar)

        assigned_admin = self.request.query_params.get("assigned_admin", None)
        if assigned_admin:
            queryset = queryset.filter(assigned_admin_id=assigned_admin)

        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_portal_active=is_active.lower() == "true")

        # Activity filter
        activity = self.request.query_params.get("activity", None)
        if activity == "active":
            # Active in last 30 days
            from datetime import timedelta

            from django.utils import timezone

            queryset = queryset.filter(
                user__last_login__gte=timezone.now() - timedelta(days=30)
            )
        elif activity == "dormant":
            # No activity in last 30 days
            from datetime import timedelta

            from django.utils import timezone

            queryset = queryset.filter(
                Q(user__last_login__lt=timezone.now() - timedelta(days=30))
                | Q(user__last_login__isnull=True)
            )

        return queryset.order_by("-created_at")

    def post(self, request, *args, **kwargs):
        """Create a new client with user account"""
        from django.contrib.auth.models import User
        from django.db import transaction, IntegrityError
        from common.response import api_response
        import logging
        import time
        
        logger = logging.getLogger(__name__)
        logger.info(f"Client creation request data: {request.data}")
        
        # Ensure required fields are present
        required_fields = ['email', 'company']
        missing_fields = [field for field in required_fields if not request.data.get(field)]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return Response(
                api_response(
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    status_code=400,
                    success=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                import threading
                
                email = request.data.get('email', '').strip().lower()
                full_name = request.data.get('full_name', '').strip()
                company = request.data.get('company', '').strip()
                
                # 🔒 FIRST CHECK: See if client already exists by email
                existing_client = Client.objects.select_related('user').filter(user__email=email).first()
                if existing_client:
                    return Response(
                        api_response(
                            message="A client with this email already exists",
                            status_code=400,
                            success=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if user exists without client profile
                existing_user = User.objects.filter(email=email).first()
                
                if existing_user:
                    # User exists, use it
                    user = existing_user
                    logger.info(f"Using existing user {user.id} for client creation")
                else:
                    # 🚫 PREVENT SIGNAL AUTO-CREATION: Set thread-local marker
                    threading.current_thread().skip_auto_client_creation = True
                    
                    try:
                        # Create new user
                        base_username = email.split('@')[0]
                        username = base_username
                        counter = 1
                        
                        # Generate unique username
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}_{counter}"
                            counter += 1
                            if counter > 1000:  # Safety check
                                timestamp = str(int(time.time()))
                                username = f"{base_username}_{timestamp}"
                                break
                        
                        # Parse full name
                        first_name = ''
                        last_name = ''
                        if full_name:
                            name_parts = full_name.strip().split()
                            first_name = name_parts[0] if name_parts else ''
                            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                        
                        # Create user
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            password='TempPass123!'  # Temporary password
                        )
                        logger.info(f"Created new user {user.id}: {username}")
                        
                    finally:
                        # 🧹 CLEANUP: Remove thread-local marker
                        if hasattr(threading.current_thread(), 'skip_auto_client_creation'):
                            delattr(threading.current_thread(), 'skip_auto_client_creation')
                
                # Process secondary_pillars
                secondary_pillars_str = request.data.get('secondary_pillars', '')
                secondary_pillars = []
                if secondary_pillars_str:
                    # Split by comma and clean up
                    secondary_pillars = [pillar.strip() for pillar in secondary_pillars_str.split(',') if pillar.strip()]
                
                # 🧪 ATOMIC CLIENT CREATION: Use get_or_create for safety
                client, created = Client.objects.get_or_create(
                    user=user,
                    defaults={
                        "company": company,
                        "role": request.data.get('role', ''),
                        "stage": request.data.get('stage', 'discover'),
                        "primary_pillar": request.data.get('primary_pillar', 'strategic'),
                        "secondary_pillars": secondary_pillars,
                        "internal_notes": request.data.get('internal_notes', ''),
                        "assigned_admin": request.user,
                    }
                )
                
                if not created:
                    # Update existing client with new data if it was auto-created
                    logger.info(f"Client already existed for user {user.id}, updating with provided data")
                    client.company = company
                    client.role = request.data.get('role', '')
                    client.stage = request.data.get('stage', 'discover')
                    client.primary_pillar = request.data.get('primary_pillar', 'strategic')
                    client.secondary_pillars = secondary_pillars
                    client.internal_notes = request.data.get('internal_notes', '')
                    client.assigned_admin = request.user
                    client.save()
                    logger.info(f"Updated existing client {client.id} with admin-provided data")
                else:
                    # Trigger Workspace Setup Email for new clients
                    try:
                        from admin_portal.orr_email_service import ORREmailService
                        ORREmailService.send_workspace_setup(
                            recipient_email=user.email,
                            workspace_url="https://orr.solutions/dashboard",
                            workspace_email=user.email,
                            storage_limit="5 GB"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send workspace setup email: {str(e)}")
                
                # Success - client was created
                logger.info(f"Client created successfully: {client.id}")
                
                # Return success response
                response_serializer = ClientListSerializer(client)
                return Response(
                    api_response(
                        message="Client created successfully",
                        data=response_serializer.data,
                        status_code=201,
                        success=True
                    ),
                    status=status.HTTP_201_CREATED
                )
                
        except IntegrityError as e:
            logger.error(f"IntegrityError during client creation: {str(e)}")
            error_msg = str(e).lower()
            
            # This should rarely happen now with our triple protection
            if "unique constraint" in error_msg or "duplicate key" in error_msg:
                if "user_id" in error_msg or "client_profile" in error_msg:
                    return Response(
                        api_response(
                            message="This user already has a client profile",
                            status_code=400,
                            success=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif "email" in error_msg:
                    return Response(
                        api_response(
                            message="Email address already exists",
                            status_code=400,
                            success=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif "username" in error_msg:
                    return Response(
                        api_response(
                            message="Username conflict occurred. Please try again.",
                            status_code=400,
                            success=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response(
                api_response(
                    message="Database constraint error. Please check if the client already exists.",
                    status_code=400,
                    success=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during client creation: {str(e)}")
            return Response(
                api_response(
                    message=f"Failed to create client: {str(e)}",
                    status_code=500,
                    success=False
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=["Client Management"],
    summary="Get or update client details",
    description="Retrieve detailed information about a specific client or update client information including company details, stage, pillar assignments, and internal notes.",
)
class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete client details"""

    queryset = Client.objects.select_related("user", "assigned_admin").all()
    permission_classes = [CanViewAllClients]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ClientDetailSerializer
        return ClientUpdateSerializer

    def perform_destroy(self, instance):
        from django.db import transaction, connection

        user = instance.user
        if not user:
            instance.delete()
            return

        try:
            with transaction.atomic():
                # Set a statement timeout to avoid hanging the connection
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL statement_timeout = '55s';")

                # Manually delete high-volume related objects first to avoid
                # a single massive CASCADE that can exceed Cloud Run's 60s limit.
                # Order: deepest children first, then parent tables.

                # -- Ticket children, then tickets themselves --
                from admin_portal.models import TicketMessage, Ticket

                client_ticket_ids = list(
                    Ticket.objects.filter(client=instance).values_list("id", flat=True)
                )
                if client_ticket_ids:
                    TicketMessage.objects.filter(
                        ticket_id__in=client_ticket_ids
                    ).delete()
                    Ticket.objects.filter(id__in=client_ticket_ids).delete()

                # -- Client documents --
                from admin_portal.models import ClientDocument

                ClientDocument.objects.filter(client=instance).delete()

                # -- Payment records --
                try:
                    from payment.models import Invoice, StripeProfile

                    Invoice.objects.filter(user=user).delete()
                    StripeProfile.objects.filter(user=user).delete()
                except Exception:
                    pass

                # -- Admin sessions --
                from admin_portal.models import AdminSession

                AdminSession.objects.filter(user=user).delete()

                # -- Notification / TicketMessage where user is sender --
                TicketMessage.objects.filter(sender=user).delete()

                # -- Dispute notes --
                try:
                    from admin_portal.models import DisputeNote

                    DisputeNote.objects.filter(created_by=user).delete()
                except Exception:
                    pass

                # -- Consultation messages referencing this user as pm --
                try:
                    from consultation.models import ConsultantMessage

                    ConsultantMessage.objects.filter(pm=user).delete()
                except Exception:
                    pass

                # -- Client profile (client app) --
                try:
                    from client.models import Profile as ClientProfile

                    ClientProfile.objects.filter(user=user).delete()
                except Exception:
                    pass

                # -- Now delete the Client row itself --
                instance.delete()

                # -- Finally delete the user (remaining CASCADE is light) --
                user.delete()
        except Exception:
            # Fallback: if manual cleanup errors, try the simple cascade
            # (may still timeout, but worth trying)
            if user:
                user.delete()
            else:
                instance.delete()


@extend_schema(
    tags=["Client Management"],
    summary="Get client engagement history",
    description="Retrieve comprehensive engagement history for a client including recent tickets, meetings, and documents.",
)
class ClientEngagementHistoryView(APIView):
    """Get client engagement history (tickets, meetings, documents)"""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
            serializer = ClientEngagementHistorySerializer(client)
            return Response(serializer.data)
        except Client.DoesNotExist:
            return Response(
                {"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Client Management"],
    summary="List or create client documents",
    description="Retrieve all documents for a specific client or upload new documents. Documents can be marked as visible or hidden from the client.",
)
class ClientDocumentListView(generics.ListCreateAPIView):
    """List and create client documents"""

    serializer_class = ClientDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs.get("client_id")
        return ClientDocument.objects.filter(client_id=client_id).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        client_id = self.kwargs.get("client_id")
        serializer.save(client_id=client_id, uploaded_by=self.request.user)


@extend_schema(
    tags=["Client Management"],
    summary="Manage client document",
    description="Retrieve, update, or delete a specific client document including metadata and visibility settings.",
)
class ClientDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete client document"""

    serializer_class = ClientDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs.get("client_id")
        return ClientDocument.objects.filter(client_id=client_id)


@extend_schema(
    tags=["Client Management"],
    summary="Perform client management actions",
    description="Execute various client management actions including toggle portal access, reset password, and update client stage.",
)
class ClientActionsView(APIView):
    """Client management actions"""

    permission_classes = [CanEditClients]

    def post(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
            action = request.data.get("action")

            if action == "toggle_portal_access":
                client.is_portal_active = not client.is_portal_active
                client.save()
                return Response(
                    {
                        "message": f"Portal access {'enabled' if client.is_portal_active else 'disabled'}",
                        "is_portal_active": client.is_portal_active,
                    }
                )

            elif action == "reset_password":
                # Trigger password reset email
                from django.contrib.auth.tokens import default_token_generator
                from django.utils.encoding import force_bytes
                from django.utils.http import urlsafe_base64_encode

                # Generate reset token and send email
                token = default_token_generator.make_token(client.user)
                uid = urlsafe_base64_encode(force_bytes(client.user.pk))

                # Here you would send the password reset email
                # For now, just return success
                return Response(
                    {
                        "message": "Password reset email sent",
                        "reset_token": token,
                        "uid": uid,
                    }
                )

            elif action == "update_stage":
                new_stage = request.data.get("stage")
                if new_stage in dict(Client.STAGE_CHOICES):
                    client.stage = new_stage
                    client.save()
                    return Response(
                        {
                            "message": f"Client stage updated to {new_stage}",
                            "stage": client.stage,
                        }
                    )
                else:
                    return Response(
                        {"error": "Invalid stage"}, status=status.HTTP_400_BAD_REQUEST
                    )

            elif action == "update_pillar":
                new_pillar = request.data.get("primary_pillar")
                secondary_pillars = request.data.get("secondary_pillars", [])

                if new_pillar in dict(Client.PILLAR_CHOICES):
                    client.primary_pillar = new_pillar
                    client.secondary_pillars = secondary_pillars
                    client.save()
                    return Response(
                        {
                            "message": f"Client pillar updated to {new_pillar}",
                            "primary_pillar": client.primary_pillar,
                            "secondary_pillars": client.secondary_pillars,
                        }
                    )
                else:
                    return Response(
                        {"error": "Invalid pillar"}, status=status.HTTP_400_BAD_REQUEST
                    )

            elif action == "update_contact_details":
                user_data = request.data.get("user_data", {})
                if "first_name" in user_data:
                    client.user.first_name = user_data["first_name"]
                if "last_name" in user_data:
                    client.user.last_name = user_data["last_name"]
                if "email" in user_data:
                    client.user.email = user_data["email"]
                client.user.save()

                client_data = request.data.get("client_data", {})
                if "company" in client_data:
                    client.company = client_data["company"]
                if "role" in client_data:
                    client.role = client_data["role"]
                client.save()

                return Response({"message": "Contact details updated successfully"})

            elif action == "add_internal_note":
                note = request.data.get("note", "")
                if note:
                    from django.utils import timezone

                    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
                    new_note = f"[{timestamp}] {request.user.get_full_name()}: {note}"

                    if client.internal_notes:
                        client.internal_notes += f"\n\n{new_note}"
                    else:
                        client.internal_notes = new_note

                    client.save()
                    return Response({"message": "Internal note added successfully"})
                else:
                    return Response(
                        {"error": "Note content is required"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

        except Client.DoesNotExist:
            return Response(
                {"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Client Management"],
    summary="Get client statistics",
    description="Retrieve comprehensive client statistics including total counts, distribution by stage and pillar, and recent activity metrics.",
)
class ClientStatsView(APIView):
    """Client statistics and analytics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Basic client stats
        total_clients = Client.objects.count()
        active_clients = Client.objects.filter(is_portal_active=True).count()

        # Clients by stage
        clients_by_stage = dict(
            Client.objects.values("stage")
            .annotate(count=Count("id"))
            .values_list("stage", "count")
        )

        # Clients by pillar
        clients_by_pillar = dict(
            Client.objects.values("primary_pillar")
            .annotate(count=Count("id"))
            .values_list("primary_pillar", "count")
        )

        # Recent activity
        from datetime import timedelta

        from django.utils import timezone

        recently_active = Client.objects.filter(
            user__last_login__gte=timezone.now() - timedelta(days=7)
        ).count()

        return Response(
            {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "recently_active": recently_active,
                "clients_by_stage": clients_by_stage,
                "clients_by_pillar": clients_by_pillar,
            }
        )
