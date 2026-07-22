from rest_framework.routers import DefaultRouter
"""
PM URL Configuration
All routes under /pm/v1/...
"""

from django.urls import path, include

from .views import (
    # Auth
    PMRegistrationView,
    PMOnboardingSubmitView,
    # Projects
    PMProjectListCreateView,
    PMProjectDetailView,
    PMProjectAssignmentsView,
    PMProjectSubmitView,
    PMProjectAdminReviewView,
    PMProjectGenerateSummaryView,
    PMProjectVersionsView,
    PMProjectDocumentUploadView,
    # Tasks
    PMTaskListCreateView,
    PMTaskDetailView,
    PMTaskSubmitReviewView,
    PMTaskReviewView,
    PMTaskCompleteView,
    # Consultant Matching
    PMConsultantMatchView,
    PMAddManualMatchView,
    PMProjectSourceExternallyView,
    # Assignments
    PMAssignmentCreateView,
    PMAssignmentDetailView,
    PMAssignmentSendInvitationView,
    PMAssignmentActivateAccessView,
    PMAssignmentAcceptView,
    PMAssignmentComplianceView,
    # Opportunities
    PMOpportunityListView,
    PMOpportunityDetailView,
    PMOpportunityRespondView,
    # Dashboard
    PMDashboardView,
    PMConsultantAssignmentsView,
    PMConsultantTasksView,
    PMConsultantProjectDetailView,
    PMConsultantProjectDocumentsView,
    PMConsultantListView,
    PMDirectoryView,
    # Meetings
    PMMeetingListView,
    
    PMMeetingDetailView,
    PMMessageDirectoryView,
    PMMessageViewSet,
)

pm_msg_router = DefaultRouter()
pm_msg_router.register(r'messages', PMMessageViewSet, basename='pm-messages')


app_name = 'pm'

urlpatterns = [
    # ── Auth ──
    path('v1/auth/register/', PMRegistrationView.as_view(), name='pm-register'),
    path('v1/auth/onboarding/submit/', PMOnboardingSubmitView.as_view(), name='pm-onboarding-submit'),

    # ── Dashboard ──
    path('v1/dashboard/', PMDashboardView.as_view(), name='dashboard'),
    path('v1/consultant/assignments/', PMConsultantAssignmentsView.as_view(), name='consultant-assignments'),
    path('v1/consultant/tasks/', PMConsultantTasksView.as_view(), name='consultant-tasks'),
    path('v1/consultant/projects/<int:pk>/', PMConsultantProjectDetailView.as_view(), name='consultant-project-detail'),
    path('v1/consultant/projects/<int:pk>/documents/', PMConsultantProjectDocumentsView.as_view(), name='consultant-project-documents'),
    path('v1/directory/', PMDirectoryView.as_view(), name='pm-directory'),
    
    # ── Consultants ──
    path('v1/consultants/', PMConsultantListView.as_view(), name='consultant-list'),

    # ── Projects ──
    path('v1/projects/', PMProjectListCreateView.as_view(), name='project-list-create'),
    path('v1/projects/<int:pk>/', PMProjectDetailView.as_view(), name='project-detail'),
    path('v1/projects/<int:pk>/assignments/', PMProjectAssignmentsView.as_view(), name='project-assignments'),
    path('v1/projects/<int:pk>/submit/', PMProjectSubmitView.as_view(), name='project-submit'),
    path('v1/projects/<int:pk>/review/', PMProjectAdminReviewView.as_view(), name='project-review'),
    path('v1/projects/<int:pk>/generate-summary/', PMProjectGenerateSummaryView.as_view(), name='project-generate-summary'),
    path('v1/projects/<int:pk>/versions/', PMProjectVersionsView.as_view(), name='project-versions'),
    path('v1/projects/<int:pk>/documents/', PMProjectDocumentUploadView.as_view(), name='project-documents'),

    # ── Tasks ──
    path('v1/projects/<int:project_pk>/tasks/', PMTaskListCreateView.as_view(), name='task-list-create'),
    path('v1/tasks/<int:pk>/', PMTaskDetailView.as_view(), name='task-detail'),
    path('v1/tasks/<int:pk>/submit-review/', PMTaskSubmitReviewView.as_view(), name='task-submit-review'),
    path('v1/tasks/<int:pk>/review/', PMTaskReviewView.as_view(), name='task-review'),
    path('v1/tasks/<int:pk>/complete/', PMTaskCompleteView.as_view(), name='task-complete'),

    # ── Consultant Matching ──
    path('v1/projects/<int:pk>/match-consultants/', PMConsultantMatchView.as_view(), name='match-consultants'),
    path('v1/projects/<int:pk>/source-externally/', PMProjectSourceExternallyView.as_view(), name='source-externally'),
    path('v1/projects/<int:pk>/matches/', PMConsultantMatchView.as_view(), name='match-results'),
    path('v1/projects/<int:pk>/matches/add/', PMAddManualMatchView.as_view(), name='match-add-manual'),

    # ── Assignments ──
    path('v1/projects/<int:pk>/assign/', PMAssignmentCreateView.as_view(), name='assignment-create'),
    path('v1/assignments/<int:pk>/', PMAssignmentDetailView.as_view(), name='assignment-detail'),
    path('v1/assignments/<int:pk>/send-invitation/', PMAssignmentSendInvitationView.as_view(), name='assignment-send-invitation'),
    path('v1/assignments/<int:pk>/activate-access/', PMAssignmentActivateAccessView.as_view(), name='assignment-activate-access'),
    path('v1/assignments/<int:pk>/accept/', PMAssignmentAcceptView.as_view(), name='assignment-accept'),
    path('v1/assignments/<int:pk>/compliance/', PMAssignmentComplianceView.as_view(), name='assignment-compliance'),

    # ── Opportunities (Consultant-facing) ──
    path('v1/opportunities/', PMOpportunityListView.as_view(), name='opportunity-list'),
    path('v1/opportunities/<int:pk>/', PMOpportunityDetailView.as_view(), name='opportunity-detail'),
    path('v1/opportunities/<int:pk>/respond/', PMOpportunityRespondView.as_view(), name='opportunity-respond'),

    # ── Meetings ──
    path('v1/meetings/', PMMeetingListView.as_view(), name='meeting-list'),
    path('v1/meetings/<int:pk>/', PMMeetingDetailView.as_view(), name='meeting-detail'),
    # 💬 Messages 💬
    path('v1/messages/directory/', PMMessageDirectoryView.as_view(), name='pm-message-directory'),
    path('v1/', include(pm_msg_router.urls)),
]
