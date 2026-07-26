from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.document import ClientDocumentsView
from .views.studio_document import StudioDocumentListView, StudioDocumentDetailView
from admin_portal.v1.views import vault
from admin_portal.v1.views import ai_views

from .views.tickets import ClientTicketCreateAPIView, ClientTicketHistoryAPIView
from .views.account import (
    AccountSettingsView,
    ChangePasswordView,
    DashboardOverviewView,
    VerifyEmailView,
)
from .views.dashboard import DashboardView, PerformanceGraphView
from .views.favourite import FavoriteDeleteView, FavoriteListView, ToggleFavoriteView
from .views.admin_auth import AdminSignupView
from .views.admin_roles import AdminRolesView
from .views.auth import LoginView, SignupView
from .views.client_auth import ClientSignupView
from .views.onboarding import OnboardingQuestionnaireViewSet
from .views.profile import CreateOrUpdateProfileView, GetProfileView
from .views.role_check import RoleCheckView
from .views.ticket import (
    ClientTicketListView,
    ClientTicketDetailView,
    ClientTicketMessagesView,
    ClientSendMessageView,
)

from .views.past_consultation import PastConsultationListView
from .views.request import (
    ClientRequestListCreateView,
    ClientRequestDetailView,
    ClientRequestSubmitView,
    ClientRequestDocumentUploadView,
    ClientRequestVersionsView,
    ClientRequestAdminListView,
    ClientRequestAdminDetailView,
    ClientRequestAdminReviewView,
    ClientRequestConvertToProjectView,
    ClientRequestAdminPMListView,
    ClientRequestAdminCreateView,
)

from .views.report import MeetingReportDashboardView

router = DefaultRouter()
router.register(r"onboarding", OnboardingQuestionnaireViewSet, basename="onboarding")


urlpatterns = [
    path("", include(router.urls)),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("register/", SignupView.as_view(), name="register"),
    path("client/register/", ClientSignupView.as_view(), name="client-register"),
    path("admin-register/", AdminSignupView.as_view(), name="admin-register"),
    path("login/", LoginView.as_view(), name="reqister"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("profile/create/", CreateOrUpdateProfileView.as_view(), name="profile-create"),
    path("account/settings/", AccountSettingsView.as_view(), name="account-settings"),
    path("activities/", DashboardOverviewView.as_view(), name="activities"),
    path("role-check/", RoleCheckView.as_view(), name="role-check"),
    path("admin-roles/", AdminRolesView.as_view(), name="admin-roles"),
    path("favorites/", FavoriteListView.as_view(), name="favorites-list"),
    path("favorites/<int:document_id>/toggle/", ToggleFavoriteView.as_view(), name="favorites-toggle"),
    path("favorites/<int:pk>/delete/", FavoriteDeleteView.as_view(), name="favorites-delete"),
    path("client/documents/", ClientDocumentsView.as_view(), name="client-documents"),
    path("profile/", GetProfileView.as_view(), name="get-profile"),
    # Ticket URLs
    path("tickets/", ClientTicketListView.as_view(), name="client-tickets"),
    path("tickets/<int:pk>/", ClientTicketDetailView.as_view(), name="client-ticket-detail"),
    path("tickets/<int:ticket_id>/messages/", ClientTicketMessagesView.as_view(), name="client-ticket-messages"),
    path("tickets/<int:ticket_id>/send-message/", ClientSendMessageView.as_view(), name="client-send-message"),
    path(
        "tickets/create/",
        ClientTicketCreateAPIView.as_view(),
        name="ticket-create",
    ),
    path(
        "tickets/history/",
        ClientTicketHistoryAPIView.as_view(),
        name="ticket-history",
    ),

    path("past-consultations/", PastConsultationListView.as_view(), name="past-consultations"),
     path(
        "dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),
    path("performance/", PerformanceGraphView.as_view(), name="performance-graph"),
    path("report/", MeetingReportDashboardView.as_view(), name="report"),
    
    # Vault URLs
    path("vault/folders/", vault.VaultFolderListView.as_view(), name="client-vault-folders"),
    path("vault/folders/<int:pk>/", vault.VaultFolderDetailView.as_view(), name="client-vault-folder-detail"),
    path("vault/documents/", vault.VaultDocumentListView.as_view(), name="client-vault-documents"),
    path("vault/documents/<int:pk>/", vault.VaultDocumentDetailView.as_view(), name="client-vault-document-detail"),
    path("vault/activity/", vault.VaultActivityListView.as_view(), name="client-vault-activity"),

    # Document Studio endpoints
    path("api/documents/", StudioDocumentListView.as_view(), name="studio-document-list"),
    path("api/documents/<int:pk>/", StudioDocumentDetailView.as_view(), name="studio-document-detail"),

    # AI Assistant endpoints
    path("ai/chat/", ai_views.AIAssistantChatView.as_view(), name="client-ai-chat"),
    path("ai/meeting-prep/", ai_views.MeetingPrepView.as_view(), name="client-ai-meeting-prep"),
    path("ai/document-summary/", ai_views.DocumentSummaryView.as_view(), name="client-ai-document-summary"),

    # Client Request / Problem Brief endpoints
    path("requests/", ClientRequestListCreateView.as_view(), name="client-request-list-create"),
    path("requests/<int:pk>/", ClientRequestDetailView.as_view(), name="client-request-detail"),
    path("requests/<int:pk>/submit/", ClientRequestSubmitView.as_view(), name="client-request-submit"),
    path("requests/<int:pk>/documents/", ClientRequestDocumentUploadView.as_view(), name="client-request-documents"),
    path("requests/<int:pk>/versions/", ClientRequestVersionsView.as_view(), name="client-request-versions"),

    # Admin-facing request endpoints
    path("api/admin/requests/", ClientRequestAdminListView.as_view(), name="admin-request-list"),
    path("api/admin/requests/create/", ClientRequestAdminCreateView.as_view(), name="admin-request-create"),
    path("api/admin/requests/<int:pk>/", ClientRequestAdminDetailView.as_view(), name="admin-request-detail"),
    path("api/admin/requests/<int:pk>/review/", ClientRequestAdminReviewView.as_view(), name="admin-request-review"),
    path(
        "api/admin/requests/<int:pk>/convert-to-project/",
        ClientRequestConvertToProjectView.as_view(),
        name="admin-client-request-convert",
    ),
    path(
        "api/admin/pms/",
        ClientRequestAdminPMListView.as_view(),
        name="admin-client-request-pms",
    ),
]
