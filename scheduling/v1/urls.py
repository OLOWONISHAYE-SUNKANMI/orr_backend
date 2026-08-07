from django.urls import  path

from .views import (
    AvailableSlotsView,
    CalendarView,
    CalendlyWebhookView,
    CreateMeetingView,
    EventTypesView,
    MeetingChangeStatusView,
    MyMeetingsView,
    UpdateMeetingPrepView,
    CreateCalendlyWebhook,
    MeetingDetailView,
    MeetingHostJoinedView,
)

urlpatterns = [
    path("mymeetings", MyMeetingsView.as_view(), name="my-meeting"),
    path("meetings/<int:pk>/", MeetingDetailView.as_view(), name="meeting-detail"),
    path(
        "meetings/<int:pk>/change-status/",
        MeetingChangeStatusView.as_view(),
        name="meeting-change-status",
    ),
    path(
        "meetings/<int:pk>/host-joined/",
        MeetingHostJoinedView.as_view(),
        name="meeting-host-joined",
    ),
    path(
        "meeting-preform/<int:pk>",
        UpdateMeetingPrepView.as_view(),
        name="meeting-preform",
    ),
    path("meeting-slots/", AvailableSlotsView.as_view()),
    path("create-meeting/", CreateMeetingView.as_view()),
    path("event-type/", EventTypesView.as_view()),
    path("calendar/", CalendarView.as_view(), name="calendar-month"),
    path("webhooks/calendly/", CalendlyWebhookView.as_view(), name="calendly-webhook"),
    path('calendly/webhook/create/', CreateCalendlyWebhook.as_view(), name='create_calendly_webhook'),
]
