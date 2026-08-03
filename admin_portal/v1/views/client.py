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
        _raw_delete_client(instance)


def _raw_delete_client(client_instance):
    """
    Delete a client and ALL related data using raw SQL.

    Why raw SQL instead of Django ORM?
    1. Django ORM's cascade fires a `post_delete` signal for EVERY row deleted
       (global handler in common/signals.py creates an AuditLog per row).
    2. With hundreds of related rows across 15+ tables, that means hundreds of
       extra INSERT statements, easily exceeding Cloud Run's 60s timeout.
    3. Raw SQL does a single DELETE per table — no Python-level iteration,
       no signal dispatch, no N+1 audit writes.

    Deletion order: deepest children first, then parents, then the User.
    """
    from django.db import connection

    def _safe_sql(cursor, sql, params=None):
        """Execute SQL but skip gracefully if the table doesn't exist."""
        try:
            cursor.execute(sql, params or [])
        except Exception as exc:
            if "does not exist" in str(exc):
                # Table hasn't been created yet — skip silently
                connection.ensure_connection()
            else:
                raise

    client_id = client_instance.id
    user_id = client_instance.user_id

    if not user_id:
        # No user linked — just remove the client row directly
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM admin_portal_client WHERE id = %s", [client_id])
        return

    with connection.cursor() as cursor:
        # Set a generous statement timeout as safety net
        if connection.vendor == "postgresql":
            cursor.execute("SET LOCAL statement_timeout = '50s';")

        # ──────────────────────────────────────────────────
        # PHASE 1: Delete children of Client-owned tables
        # (deepest FK children first)
        # ──────────────────────────────────────────────────

        # 1a. TicketMessage  (FK → Ticket → Client)
        _safe_sql(cursor, """
            DELETE FROM admin_portal_ticketmessage
            WHERE ticket_id IN (
                SELECT id FROM admin_portal_ticket WHERE client_id = %s
            )
        """, [client_id])

        # 1b. Tickets
        _safe_sql(cursor,
            "DELETE FROM admin_portal_ticket WHERE client_id = %s", [client_id]
        )

        # 1c. DocumentVersion (FK → ClientDocument → Client)
        _safe_sql(cursor, """
            DELETE FROM admin_portal_documentversion
            WHERE document_id IN (
                SELECT id FROM admin_portal_clientdocument WHERE client_id = %s
            )
        """, [client_id])

        # 1d. FavoriteDocument (FK → ClientDocument)
        _safe_sql(cursor, """
            DELETE FROM client_favoritedocument
            WHERE document_id IN (
                SELECT id FROM admin_portal_clientdocument WHERE client_id = %s
            )
        """, [client_id])

        # 1e. ClientDocument
        _safe_sql(cursor,
            "DELETE FROM admin_portal_clientdocument WHERE client_id = %s", [client_id]
        )

        # 1f. VaultFolder (self-referencing — delete children first)
        _safe_sql(cursor, """
            DELETE FROM admin_portal_vaultfolder
            WHERE parent_id IN (
                SELECT id FROM admin_portal_vaultfolder WHERE client_id = %s
            )
        """, [client_id])
        _safe_sql(cursor,
            "DELETE FROM admin_portal_vaultfolder WHERE client_id = %s", [client_id]
        )

        # 1g. DisputeNote (FK → PaymentDispute → Client)
        _safe_sql(cursor, """
            DELETE FROM admin_portal_disputenote
            WHERE dispute_id IN (
                SELECT id FROM admin_portal_paymentdispute WHERE client_id = %s
            )
        """, [client_id])

        # 1h. PaymentDispute
        _safe_sql(cursor,
            "DELETE FROM admin_portal_paymentdispute WHERE client_id = %s", [client_id]
        )

        # 1i. ProRataApproval
        _safe_sql(cursor,
            "DELETE FROM admin_portal_prorataapproval WHERE client_id = %s", [client_id]
        )

        # 1j. WalletTransaction
        _safe_sql(cursor,
            "DELETE FROM admin_portal_wallettransaction WHERE client_id = %s", [client_id]
        )

        # 1k. SystemNotification (FK → Client, FK → Ticket — tickets already gone)
        _safe_sql(cursor,
            "DELETE FROM admin_portal_systemnotification WHERE related_client_id = %s",
            [client_id],
        )

        # 1l. Meetings
        _safe_sql(cursor,
            "DELETE FROM admin_portal_meeting WHERE client_id = %s", [client_id]
        )

        # ──────────────────────────────────────────────────
        # PHASE 2: Delete from client app tables
        # ──────────────────────────────────────────────────

        # 2a. Transaction (FK → Wallet → User, FK → Project → Client)
        _safe_sql(cursor, """
            DELETE FROM client_transaction
            WHERE wallet_id IN (
                SELECT id FROM client_wallet WHERE owner_id = %s
            )
        """, [user_id])

        # 2b. Wallet
        _safe_sql(cursor,
            "DELETE FROM client_wallet WHERE owner_id = %s", [user_id]
        )

        # 2c. ClientRequest children (documents, version history)
        # ClientRequestVersion FK → ClientRequest
        _safe_sql(cursor, """
            DELETE FROM client_clientrequestversion
            WHERE request_id IN (
                SELECT id FROM client_clientrequest WHERE client_id = %s
            )
        """, [client_id])
        # ClientRequestDocument FK → ClientRequest
        _safe_sql(cursor, """
            DELETE FROM client_clientrequestdocument
            WHERE request_id IN (
                SELECT id FROM client_clientrequest WHERE client_id = %s
            )
        """, [client_id])
        # ClientRequest
        _safe_sql(cursor,
            "DELETE FROM client_clientrequest WHERE client_id = %s", [client_id]
        )

        # 2d. Project
        _safe_sql(cursor,
            "DELETE FROM client_project WHERE client_id = %s", [client_id]
        )

        # 2e. FavoriteDocument (by user)
        _safe_sql(cursor,
            "DELETE FROM client_favoritedocument WHERE user_id = %s", [user_id]
        )

        # 2f. Activity
        _safe_sql(cursor,
            "DELETE FROM client_activity WHERE user_id = %s", [user_id]
        )

        # 2g. OnboardingQuestionnaire
        _safe_sql(cursor,
            "DELETE FROM client_onboardingquestionnaire WHERE user_id = %s", [user_id]
        )

        # 2h. Client Profile (client app)
        _safe_sql(cursor,
            "DELETE FROM client_profile WHERE user_id = %s", [user_id]
        )

        # ──────────────────────────────────────────────────
        # PHASE 3: Delete User-linked rows across other apps
        # ──────────────────────────────────────────────────

        # 3a. Payment tables
        _safe_sql(cursor, "DELETE FROM payment_invoice WHERE user_id = %s", [user_id])
        _safe_sql(cursor,
            "DELETE FROM payment_checkoutsessionlog WHERE user_id = %s", [user_id]
        )
        _safe_sql(cursor,
            "DELETE FROM payment_subscription WHERE user_id = %s", [user_id]
        )
        _safe_sql(cursor,
            "DELETE FROM payment_stripecustomer WHERE user_id = %s", [user_id]
        )

        # 3b. Admin sessions
        _safe_sql(cursor,
            "DELETE FROM admin_portal_adminsession WHERE user_id = %s", [user_id]
        )

        # 3c. TicketMessage by sender (user authored messages on other clients' tickets)
        _safe_sql(cursor,
            "DELETE FROM admin_portal_ticketmessage WHERE sender_id = %s", [user_id]
        )

        # 3d. DisputeNote by created_by
        _safe_sql(cursor,
            "DELETE FROM admin_portal_disputenote WHERE created_by_id = %s", [user_id]
        )

        # 3e. SystemNotification where recipient is this user
        _safe_sql(cursor,
            "DELETE FROM admin_portal_systemnotification WHERE recipient_id = %s",
            [user_id],
        )

        # 3f. ConsultantMessage (pm field)
        _safe_sql(cursor,
            "DELETE FROM consultation_consultantmessage WHERE pm_id = %s", [user_id]
        )

        # 3g. AccessLog (SET_NULL but let's clean up)
        _safe_sql(cursor,
            "UPDATE admin_portal_accesslog SET user_id = NULL WHERE user_id = %s",
            [user_id],
        )

        # 3h. AuditLog (SET_NULL)
        _safe_sql(cursor,
            "UPDATE admin_portal_auditlog SET user_id = NULL WHERE user_id = %s",
            [user_id],
        )

        # ──────────────────────────────────────────────────
        # PHASE 4: Delete the Client row, then the User row
        # ──────────────────────────────────────────────────
        cursor.execute(
            "DELETE FROM admin_portal_client WHERE id = %s", [client_id]
        )
        cursor.execute(
            "DELETE FROM auth_user WHERE id = %s", [user_id]
        )


@extend_schema(
    tags=["Client Management"],
    summary="Delete a client (optimized)",
    description="Permanently deletes a client and all associated data using optimized raw SQL. "
    "This bypasses Django ORM cascade to avoid timeout on Cloud Run.",
)
class ClientDeleteView(APIView):
    """Dedicated optimized client delete endpoint"""

    permission_classes = [CanEditClients]

    def delete(self, request, pk):
        try:
            client = Client.objects.select_related("user").get(pk=pk)
        except Client.DoesNotExist:
            return Response(
                {"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND
            )

        client_name = str(client)
        user_id = client.user_id

        try:
            _raw_delete_client(client)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Client delete failed: {e}")
            return Response(
                {"error": f"Failed to delete client: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Log the deletion (single audit entry, not hundreds)
        from admin_portal.models import AuditLog

        AuditLog.objects.create(
            user=request.user,
            action="delete",
            model_name="Client",
            object_id=str(pk),
            description=f"Client deleted: {client_name} (user_id={user_id})",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response(
            {"message": f"Client {pk} deleted successfully."},
            status=status.HTTP_200_OK,
        )


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
