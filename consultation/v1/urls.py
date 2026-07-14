from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConsultantRegistrationView,
    ConsultantVerificationView,
    ConsultantOnboardingView,
    ConsultantProfileView,
    ConsultantJobViewSet,
    ConsultantTaskViewSet,
    ConsultantInvoiceViewSet,
    ConsultantDocumentViewSet,
    ConsultantMessageViewSet,
    ConsultantMeetingViewSet,
    ConsultantNotificationViewSet,
    ConsultantDocumentListView,
    ConsultantDocumentDetailView,
    ConsultantMessageDirectoryView
)

job_router = DefaultRouter()
job_router.register(r'jobs', ConsultantJobViewSet, basename='consultant-jobs')

task_router = DefaultRouter()
task_router.register(r'tasks', ConsultantTaskViewSet, basename='consultant-tasks')

invoice_router = DefaultRouter()
invoice_router.register(r'invoices', ConsultantInvoiceViewSet, basename='consultant-invoices')

msg_router = DefaultRouter()
msg_router.register(r'messages', ConsultantMessageViewSet, basename='consultant-messages')

mtg_router = DefaultRouter()
mtg_router.register(r'meetings', ConsultantMeetingViewSet, basename='consultant-meetings')

notif_router = DefaultRouter()
notif_router.register(r'notifications', ConsultantNotificationViewSet, basename='consultant-notifications')

urlpatterns = [
    path('auth/register/', ConsultantRegistrationView.as_view(), name='consultant-register'),
    path('auth/verify/', ConsultantVerificationView.as_view(), name='consultant-verify'),
    path('<str:consultant_id>/onboarding/', ConsultantOnboardingView.as_view(), name='consultant-onboarding'),
    path('<str:consultant_id>/profile/', ConsultantProfileView.as_view(), name='consultant-profile'),
    
    path('<str:consultant_id>/documents/', ConsultantDocumentListView.as_view(), name='consultant-documents'),
    path('<str:consultant_id>/documents/<int:pk>/', ConsultantDocumentDetailView.as_view(), name='consultant-document-detail'),
    path('<str:consultant_id>/messages/directory/', ConsultantMessageDirectoryView.as_view(), name='consultant-message-directory'),
    
    path('<str:consultant_id>/', include(job_router.urls)),
    path('<str:consultant_id>/', include(task_router.urls)),
    path('<str:consultant_id>/', include(invoice_router.urls)),
    path('<str:consultant_id>/', include(msg_router.urls)),
    path('<str:consultant_id>/', include(mtg_router.urls)),
    path('<str:consultant_id>/', include(notif_router.urls)),
]
