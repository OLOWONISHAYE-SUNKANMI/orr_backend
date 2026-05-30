from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ai_oversight,
    analytics,
    approval_queue,
    audit_security,
    auth,
    auto_reply,
    behavior_analytics,
    billing,
    billing_overview,
    client,
    client_profile,
    cms,
    cms_comprehensive,
    compliance,
    consultation_metrics,
    content,
    dashboard,
    funnel_reports,
    invoicing,
    meeting,
    notifications,
    payment_disputes,
    prorata_approvals,
    role_management,
    search,
    sector_insights,
    settings,
    subscriptions,
    system_config,
    system_health,
    ticket,
    vault,
    wallet_logs,
    workspace_usage,
)
from .. import views_google

# Authentication URLs
auth_patterns = [
    path("me/", auth.CurrentUserRoleView.as_view(), name="current-user-role"),
    path(
        "check-permission/", auth.CheckPermissionView.as_view(), name="check-permission"
    ),
]

# Dashboard URLs
dashboard_patterns = [
    path(
        "overview/",
        dashboard.DashboardOverviewView.as_view(),
        name="dashboard-overview",
    ),
    path(
        "recent-activity/",
        dashboard.RecentActivityView.as_view(),
        name="dashboard-recent-activity",
    ),
    path(
        "quick-stats/", dashboard.QuickStatsView.as_view(), name="dashboard-quick-stats"
    ),
    path(
        "client-widgets/",
        dashboard.ClientDashboardWidgetsView.as_view(),
        name="dashboard-client-widgets",
    ),
]

# Client Management URLs
client_patterns = [
    path("", client.ClientListView.as_view(), name="client-list"),
    path("<int:pk>/", client.ClientDetailView.as_view(), name="client-detail"),
    path(
        "<int:pk>/complete-profile/",
        client_profile.ClientCompleteProfileView.as_view(),
        name="client-complete-profile",
    ),
    path(
        "<int:pk>/engagement-history/",
        client.ClientEngagementHistoryView.as_view(),
        name="client-engagement-history",
    ),
    path(
        "<int:pk>/actions/", client.ClientActionsView.as_view(), name="client-actions"
    ),
    path(
        "<int:client_id>/documents/",
        client.ClientDocumentListView.as_view(),
        name="client-documents",
    ),
    path(
        "<int:client_id>/documents/<int:pk>/",
        client.ClientDocumentDetailView.as_view(),
        name="client-document-detail",
    ),
    path("stats/", client.ClientStatsView.as_view(), name="client-stats"),
]

# Ticket Management URLs
ticket_patterns = [
    path("", ticket.TicketListView.as_view(), name="ticket-list"),
    path("<int:pk>/", ticket.TicketDetailView.as_view(), name="ticket-detail"),
    path(
        "<int:pk>/actions/", ticket.TicketActionsView.as_view(), name="ticket-actions"
    ),
    path(
        "<int:ticket_id>/messages/",
        ticket.TicketMessagesView.as_view(),
        name="ticket-messages",
    ),
    path("my-tickets/", ticket.MyTicketsView.as_view(), name="my-tickets"),
    path("assignable-users/", ticket.TicketAssignableUsersView.as_view(), name="ticket-assignable-users"),
    path("stats/", ticket.TicketStatsView.as_view(), name="ticket-stats"),
    # Auto-reply URLs
    path(
        "<int:ticket_id>/auto-reply/",
        auto_reply.AutoReplyView.as_view(),
        name="ticket-auto-reply"
    ),
    path(
        "<int:ticket_id>/schedule-reply/",
        auto_reply.ScheduleAutoReplyView.as_view(),
        name="ticket-schedule-reply"
    ),
    path(
        "auto-reply-templates/",
        auto_reply.AutoReplyTemplatesView.as_view(),
        name="auto-reply-templates"
    ),
]

# Content Management URLs
content_patterns = [
    path("", content.ContentListView.as_view(), name="content-list"),
    path("<int:pk>/", content.ContentDetailView.as_view(), name="content-detail"),
    path(
        "<int:pk>/publish/",
        content.ContentPublishView.as_view(),
        name="content-publish",
    ),
    path(
        "<int:pk>/preview/",
        content.ContentPreviewView.as_view(),
        name="content-preview",
    ),
    path(
        "<int:pk>/versions/",
        content.ContentVersionsView.as_view(),
        name="content-versions",
    ),
    path(
        "bulk-actions/",
        content.ContentBulkActionsView.as_view(),
        name="content-bulk-actions",
    ),
    path("stats/", content.ContentStatsView.as_view(), name="content-stats"),
    path(
        "<int:pk>/view/",
        content.ContentViewCountView.as_view(),
        name="content-view-count",
    ),
]

# Meeting Management URLs
meeting_patterns = [
    path("", meeting.MeetingListView.as_view(), name="meeting-list"),
    path("<int:pk>/", meeting.MeetingDetailView.as_view(), name="meeting-detail"),
    path(
        "<int:pk>/actions/",
        meeting.MeetingActionsView.as_view(),
        name="meeting-actions",
    ),
    path(
        "<int:pk>/assign/", meeting.MeetingAssignView.as_view(), name="meeting-assign"
    ),
    path("my-meetings/", meeting.MyMeetingsView.as_view(), name="my-meetings"),
    path("confirmed/", meeting.ConfirmedMeetingsView.as_view(), name="confirmed-meetings"),
    path("requested/", meeting.RequestedMeetingsView.as_view(), name="requested-meetings"),
    path("upcoming/", meeting.UpcomingMeetingsView.as_view(), name="upcoming-meetings"),
    path("stats/", meeting.MeetingStatsView.as_view(), name="meeting-stats"),
]

# Analytics URLs
analytics_patterns = [
    path(
        "overview/",
        analytics.AnalyticsOverviewView.as_view(),
        name="analytics-overview",
    ),
    path("clients/", analytics.ClientAnalyticsView.as_view(), name="client-analytics"),
    path(
        "content/", analytics.ContentAnalyticsView.as_view(), name="content-analytics"
    ),
    path("export/", analytics.ExportAnalyticsView.as_view(), name="export-analytics"),
]

# Behavior Analytics URLs
behavior_analytics_patterns = [
    path(
        "user-behavior/",
        behavior_analytics.UserBehaviorPatternsView.as_view(),
        name="user-behavior-patterns",
    ),
    path(
        "user-journey/",
        behavior_analytics.UserJourneyAnalyticsView.as_view(),
        name="user-journey-analytics",
    ),
]

# Sector Insights URLs
sector_insights_patterns = [
    path(
        "sector-analytics/",
        sector_insights.SectorAnalyticsView.as_view(),
        name="sector-analytics",
    ),
    path(
        "industry-benchmarks/",
        sector_insights.IndustryBenchmarksView.as_view(),
        name="industry-benchmarks",
    ),
]

# Consultation Metrics URLs
consultation_metrics_patterns = [
    path(
        "performance/",
        consultation_metrics.ConsultationPerformanceView.as_view(),
        name="consultation-performance",
    ),
    path(
        "scheduling-analytics/",
        consultation_metrics.ConsultationSchedulingAnalyticsView.as_view(),
        name="consultation-scheduling-analytics",
    ),
]

# Workspace Usage URLs
workspace_usage_patterns = [
    path(
        "analytics/",
        workspace_usage.WorkspaceUsageAnalyticsView.as_view(),
        name="workspace-usage-analytics",
    ),
    path(
        "feature-adoption/",
        workspace_usage.FeatureAdoptionAnalyticsView.as_view(),
        name="feature-adoption-metrics",
    ),
]

# Funnel Reports URLs
funnel_reports_patterns = [
    path(
        "conversion-funnel/",
        funnel_reports.ConversionFunnelAnalyticsView.as_view(),
        name="conversion-funnel-analytics",
    ),
    path(
        "time-based-funnel/",
        funnel_reports.TimeBasedFunnelAnalysisView.as_view(),
        name="time-based-funnel-analysis",
    ),
]

# Notifications URLs
notification_patterns = [
    path("", notifications.NotificationListView.as_view(), name="notification-list"),
    path(
        "<int:pk>/",
        notifications.NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "<int:pk>/actions/",
        notifications.NotificationActionsView.as_view(),
        name="notification-actions",
    ),
    path(
        "bulk-actions/",
        notifications.NotificationBulkActionsView.as_view(),
        name="notification-bulk-actions",
    ),
    path(
        "stats/",
        notifications.NotificationStatsView.as_view(),
        name="notification-stats",
    ),
]

# AI Oversight URLs
ai_oversight_patterns = [
    path(
        "conversations/",
        ai_oversight.AIConversationListView.as_view(),
        name="ai-conversation-list",
    ),
    path(
        "conversations/<int:pk>/",
        ai_oversight.AIConversationDetailView.as_view(),
        name="ai-conversation-detail",
    ),
    path(
        "conversations/<int:pk>/actions/",
        ai_oversight.AIConversationActionsView.as_view(),
        name="ai-conversation-actions",
    ),
    path(
        "stats/",
        ai_oversight.AIConversationStatsView.as_view(),
        name="ai-conversation-stats",
    ),
]

# Settings & System Config URLs
settings_patterns = [
    path("system/", settings.SystemSettingsView.as_view(), name="system-settings"),
    path("roles/", settings.AdminRoleListView.as_view(), name="admin-role-list"),
    path(
        "roles/<int:pk>/",
        settings.AdminRoleDetailView.as_view(),
        name="admin-role-detail",
    ),
    path("users/", settings.AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "users/create/",
        settings.CreateAdminUserView.as_view(),
        name="create-admin-user",
    ),
    path(
        "users/<int:pk>/",
        settings.AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path(
        "users/<int:pk>/actions/",
        settings.UserManagementActionsView.as_view(),
        name="user-management-actions",
    ),
    path("audit-logs/", settings.AuditLogListView.as_view(), name="audit-log-list"),
]

# System Health URLs
system_health_patterns = [
    path("health/", system_health.SystemHealthView.as_view(), name="system-health"),
    path(
        "performance/",
        system_health.SystemPerformanceView.as_view(),
        name="system-performance",
    ),
]

# Search & Navigation URLs
search_patterns = [
    path("global/", search.GlobalSearchView.as_view(), name="global-search"),
    path("quick/", search.QuickSearchView.as_view(), name="quick-search"),
]

# Compliance & Data Management URLs
compliance_patterns = [
    path(
        "export-client-data/",
        compliance.ClientDataExportView.as_view(),
        name="export-client-data",
    ),
    path(
        "delete-client-data/",
        compliance.ClientDataDeletionView.as_view(),
        name="delete-client-data",
    ),
    path(
        "compliance-report/",
        compliance.ComplianceReportView.as_view(),
        name="compliance-report",
    ),
]

# Role Management URLs (Super Admin only)
role_management_patterns = [
    path(
        "roles/<int:role_id>/permissions/",
        role_management.UpdateRolePermissionsView.as_view(),
        name="update-role-permissions",
    ),
    path(
        "users/<int:user_id>/deactivate/",
        role_management.DeactivateUserView.as_view(),
        name="deactivate-user",
    ),
    path(
        "users/<int:user_id>/edit/",
        role_management.EditUserView.as_view(),
        name="edit-user",
    ),
]

# Billing URLs (Admin only)
billing_patterns = [
    path("", billing.AdminBillingHistoryView.as_view(), name="admin-billing-history"),
    path("stats/", billing.AdminBillingStatsView.as_view(), name="admin-billing-stats"),
]

# Billing Overview URLs
billing_overview_patterns = [
    path("", billing_overview.BillingOverviewView.as_view(), name="billing-overview"),
    path("subscriptions/", billing_overview.SubscriptionAnalyticsView.as_view(), name="subscription-analytics"),
]

# Wallet Logs URLs
wallet_logs_patterns = [
    path(
        "wallets/",
        wallet_logs.WalletListView.as_view(),
        name="wallet-list",
    ),
    path(
        "transactions/",
        wallet_logs.WalletTransactionLogsView.as_view(),
        name="wallet-transaction-logs",
    ),
    path(
        "activity-analytics/",
        wallet_logs.PaymentActivityAnalyticsView.as_view(),
        name="payment-activity-analytics",
    ),
    path(
        "audit-trail/",
        wallet_logs.TransactionAuditTrailView.as_view(),
        name="transaction-audit-trail",
    ),
    path(
        "adjust-balance/",
        wallet_logs.WalletBalanceAdjustmentView.as_view(),
        name="wallet-adjust-balance",
    ),
]

# Pro-rata Approvals URLs
prorata_approvals_patterns = [
    path(
        "requests/",
        prorata_approvals.ProRataBillingRequestsView.as_view(),
        name="prorata-billing-requests",
    ),
    path(
        "decision/",
        prorata_approvals.ProRataApprovalDecisionView.as_view(),
        name="prorata-approval-decision",
    ),
    path(
        "calculation-preview/",
        prorata_approvals.ProRataCalculationPreviewView.as_view(),
        name="prorata-calculation-preview",
    ),
    path(
        "history/",
        prorata_approvals.ProRataApprovalHistoryView.as_view(),
        name="prorata-approval-history",
    ),
]

# Subscriptions URLs
subscriptions_patterns = [
    path(
        "management/",
        subscriptions.SubscriptionManagementView.as_view(),
        name="subscription-management",
    ),
    path(
        "<str:subscription_id>/",
        subscriptions.SubscriptionDetailView.as_view(),
        name="subscription-detail",
    ),
    path(
        "<str:subscription_id>/actions/",
        subscriptions.SubscriptionActionsView.as_view(),
        name="subscription-actions",
    ),
]

# Invoicing URLs
invoicing_patterns = [
    path(
        "overview/",
        invoicing.InvoicingOverviewView.as_view(),
        name="invoicing-overview",
    ),
    path(
        "generate/",
        invoicing.InvoiceGenerationView.as_view(),
        name="invoice-generation",
    ),
    path(
        "<str:invoice_id>/actions/",
        invoicing.InvoiceActionsView.as_view(),
        name="invoice-actions",
    ),
    path(
        "analytics/",
        invoicing.InvoiceAnalyticsView.as_view(),
        name="invoice-analytics",
    ),
]

# Payment Disputes URLs
payment_disputes_patterns = [
    path(
        "overview/",
        payment_disputes.PaymentDisputesOverviewView.as_view(),
        name="payment-disputes-overview",
    ),
    path(
        "<str:dispute_id>/actions/",
        payment_disputes.DisputeActionsView.as_view(),
        name="dispute-actions",
    ),
    path(
        "<str:dispute_id>/",
        payment_disputes.DisputeDetailView.as_view(),
        name="dispute-detail",
    ),
    path(
        "analytics/",
        payment_disputes.DisputeAnalyticsView.as_view(),
        name="dispute-analytics",
    ),
]

# CMS URLs
cms_patterns = [
    path("all-content/", cms.AllContentView.as_view(), name="cms-all-content"),
    path("homepage-content/", cms.AllHomepageContentView.as_view(), name="cms-homepage-content"),
    path("homepage/", cms.HomePageView.as_view(), name="cms-homepage"),
    path("services-page/", cms.ServicesPageView.as_view(), name="cms-services-page"),
    path("resources-page/", cms.ResourcesBlogsPageView.as_view(), name="cms-resources-page"),
    path("legacy-page/", cms.LegacyPolicyPageView.as_view(), name="cms-legacy-page"),
    path("contact-page/", cms.ContactPageView.as_view(), name="cms-contact-page"),
    path("approach-section/", cms.ApproachSectionView.as_view(), name="cms-approach-section"),
    path("business-system-section/", cms.BusinessSystemSectionView.as_view(), name="cms-business-system-section"),
    path("business-system-cards/", cms.BusinessSystemCardListView.as_view(), name="cms-business-system-cards"),
    path("business-system-cards/<int:pk>/", cms.BusinessSystemCardDetailView.as_view(), name="cms-business-system-card-detail"),
    path("orr-role-section/", cms.ORRRoleSectionView.as_view(), name="cms-orr-role-section"),
    path("message-strip/", cms.MessageStripView.as_view(), name="cms-message-strip"),
    path("process-section/", cms.ProcessSectionView.as_view(), name="cms-process-section"),
    path("orr-report-section/", cms.ORRReportSectionView.as_view(), name="cms-orr-report-section"),
    path("upload-image/", cms.ImageUploadView.as_view(), name="cms-upload-image"),
    path("service-cards/", cms.ServiceCardListView.as_view(), name="cms-service-cards"),
    path("service-cards/<int:pk>/", cms.ServiceCardDetailView.as_view(), name="cms-service-card-detail"),
    path("testimonials/", cms.TestimonialListView.as_view(), name="cms-testimonials"),
    path("testimonials/<int:pk>/", cms.TestimonialDetailView.as_view(), name="cms-testimonial-detail"),
    path("faqs/", cms.FAQListView.as_view(), name="cms-faqs"),
    path("faqs/<int:pk>/", cms.FAQDetailView.as_view(), name="cms-faq-detail"),
    path("blog/", cms.BlogPostListView.as_view(), name="cms-blog"),
    path("blog/<int:pk>/", cms.BlogPostDetailView.as_view(), name="cms-blog-detail"),
    path("blog/<int:pk>/publish/", cms.BlogPostPublishView.as_view(), name="cms-blog-publish"),
    path("contact-info/", cms.ContactInfoView.as_view(), name="cms-contact-info"),
    path("site-settings/", cms.SiteSettingsView.as_view(), name="cms-settings"),
    # New comprehensive CMS endpoints
    path("how-we-operate/", cms_comprehensive.HowWeOperatePageView.as_view(), name="cms-how-we-operate"),
    path("services-content/", cms_comprehensive.ServicesPageContentView.as_view(), name="cms-services-content"),
    path("resources-content/", cms_comprehensive.ResourcesBlogsPageContentView.as_view(), name="cms-resources-content"),
    path("legal-policy-content/", cms_comprehensive.LegalPolicyPageContentView.as_view(), name="cms-legal-policy-content"),
    path("contact-content/", cms_comprehensive.ContactPageContentView.as_view(), name="cms-contact-content"),
    path("service-stages/<int:pk>/", cms_comprehensive.ServiceStageDetailView.as_view(), name="cms-service-stage-detail"),
    path("service-pillars/<int:pk>/", cms_comprehensive.ServicePillarDetailView.as_view(), name="cms-service-pillar-detail"),
    path("process-steps/<int:pk>/", cms_comprehensive.ProcessStepDetailView.as_view(), name="cms-process-step-detail"),
    path("content-cards/<int:pk>/", cms_comprehensive.ContentCardDetailView.as_view(), name="cms-content-card-detail"),
    path("policy-items/<int:pk>/", cms_comprehensive.PolicyItemDetailView.as_view(), name="cms-policy-item-detail"),
    # New service pillar pages
    path("strategic-advisory/", cms_comprehensive.StrategicAdvisoryPageView.as_view(), name="cms-strategic-advisory"),
    path("operational-systems/", cms_comprehensive.OperationalSystemsPageView.as_view(), name="cms-operational-systems"),
    path("living-systems/", cms_comprehensive.LivingSystemsPageView.as_view(), name="cms-living-systems"),
]

# Document Vault (Google Integration) URLs
vault_patterns = [
    path("documents/", vault.VaultDocumentListView.as_view(), name="vault-documents-list"),
    path("documents/<int:pk>/", vault.VaultDocumentDetailView.as_view(), name="vault-document-detail"),
    path("documents/create-google-doc/", views_google.create_google_doc, name="vault-create-google-doc"),
    path("documents/batch-update/", vault.batch_update_documents, name="vault-documents-batch-update"),
    path("folders/", vault.VaultFolderListView.as_view(), name="vault-folders-list"),
    path("activity/", vault.VaultActivityListView.as_view(), name="vault-activity-list"),
]

approval_queue_patterns = [
    path("", approval_queue.ApprovalQueueListView.as_view(), name="approval-queue-list"),
    path("<str:req_id>/decide/", approval_queue.ApprovalQueueDecideView.as_view(), name="approval-queue-decide"),
]

audit_security_patterns = [
    path("logs/", audit_security.SecurityAuditLogListView.as_view(), name="security-audit-logs"),
    path("sessions/", audit_security.AdminSessionListView.as_view(), name="admin-sessions-list"),
    path("sessions/<str:session_id>/", audit_security.AdminSessionRevokeView.as_view(), name="admin-session-revoke"),
    path("revoke-all/", audit_security.AdminRevokeAllSessionsView.as_view(), name="admin-revoke-all-sessions"),
]

system_config_patterns = [
    path("config/", system_config.SystemConfigView.as_view(), name="system-config"),
    path("backup/", system_config.SystemBackupView.as_view(), name="system-backup"),
]

urlpatterns = [
    path("vault/", include(vault_patterns)),
    path("auth/", include(auth_patterns)),
    path("dashboard/", include(dashboard_patterns)),
    path("clients/", include(client_patterns)),
    path("tickets/", include(ticket_patterns)),
    path("content/", include(content_patterns)),
    path("meetings/", include(meeting_patterns)),
    path("analytics/", include(analytics_patterns)),
    path("behavior-analytics/", include(behavior_analytics_patterns)),
    path("sector-insights/", include(sector_insights_patterns)),
    path("consultation-metrics/", include(consultation_metrics_patterns)),
    path("workspace-usage/", include(workspace_usage_patterns)),
    path("funnel-reports/", include(funnel_reports_patterns)),
    path("notifications/", include(notification_patterns)),
    path("ai-oversight/", include(ai_oversight_patterns)),
    path("settings/", include(settings_patterns)),
    path("search/", include(search_patterns)),
    path("compliance/", include(compliance_patterns)),
    path("role-management/", include(role_management_patterns)),
    path("system/", include(system_health_patterns)),
    path("billing-history/", include(billing_patterns)),
    path("billing-overview/", include(billing_overview_patterns)),
    path("wallet-logs/", include(wallet_logs_patterns)),
    path("prorata-approvals/", include(prorata_approvals_patterns)),
    path("subscriptions/", include(subscriptions_patterns)),
    path("invoicing/", include(invoicing_patterns)),
    path("payment-disputes/", include(payment_disputes_patterns)),
    path("cms/", include(cms_patterns)),
    path("approvals/queue/", include(approval_queue_patterns)),
    path("audit/", include(audit_security_patterns)),
    path("security/", include(audit_security_patterns)),
    path("system/", include(system_config_patterns)),
]
