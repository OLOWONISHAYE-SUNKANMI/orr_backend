"""
ORR Email Service
Central service for sending all branded emails using the ORR email template suite.
Templates are stored in templates/orr_emails/ and use {{placeholder}} syntax.
"""

import logging
import os
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

# Path to the email templates directory
TEMPLATE_DIR = os.path.join(settings.BASE_DIR, 'templates', 'orr_emails')


class ORREmailService:
    """
    Central service for sending all branded ORR emails.
    Each method loads the appropriate HTML template, fills in placeholders,
    and sends via Django's send_mail (SMTP or Brevo).
    """

    @staticmethod
    def _render(template_filename: str, context: dict) -> str:
        """Load an HTML template file and replace all {{placeholder}} with context values."""
        template_path = os.path.join(TEMPLATE_DIR, template_filename)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
        except FileNotFoundError:
            logger.error(f"Email template not found: {template_path}")
            return f"<p>Email template '{template_filename}' not found.</p>"

        for key, value in context.items():
            html = html.replace('{{' + key + '}}', str(value))
        return html

    @staticmethod
    def _send(subject: str, recipient: str, html: str, plain_text: str = ''):
        """Send an email with HTML content via Django SMTP asynchronously in background thread."""
        import threading

        def send_async():
            recipients = [recipient] if isinstance(recipient, str) else recipient
            for rec in recipients:
                try:
                    send_mail(
                        subject=subject,
                        message=plain_text or subject,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[rec],
                        html_message=html,
                        fail_silently=False,
                    )
                    logger.info(f"ORR Email sent via SMTP: '{subject}' → {rec}")
                except Exception as smtp_e:
                    logger.error(f"ORR Email failed: '{subject}' → {rec}: {smtp_e}")

        thread = threading.Thread(target=send_async)
        thread.daemon = True
        thread.start()
        return True

    # ──────────────────────────────────────────────
    # 1. AUTHENTICATION & ONBOARDING
    # ──────────────────────────────────────────────

    @classmethod
    def send_email_verification(cls, recipient_email: str, verification_link: str, verification_token: str):
        """01 — Email verification on signup."""
        html = cls._render('01-email-verification.html', {
            'verification_link': verification_link,
            'verification_token': verification_token,
        })
        return cls._send('Verify Your Email - ORR Solutions', recipient_email, html,
                         f'Verify your email: {verification_link}')

    @classmethod
    def send_password_reset(cls, recipient_email: str, reset_link: str):
        """02 — Password reset."""
        html = cls._render('02-password-reset.html', {
            'reset_link': reset_link,
        })
        return cls._send('Reset Your Password - ORR Solutions', recipient_email, html,
                         f'Reset your password: {reset_link}')

    @classmethod
    def send_login_alert(cls, recipient_email: str, login_time: str, ip_address: str,
                         location: str, secure_account_link: str):
        """03 — Login from new device/location."""
        html = cls._render('03-login-alert.html', {
            'login_time': login_time,
            'ip_address': ip_address,
            'location': location,
            'secure_account_link': secure_account_link,
        })
        return cls._send('New Login Detected - ORR Solutions', recipient_email, html)

    @classmethod
    def send_welcome_email(cls, recipient_email: str, dashboard_url: str = 'https://orr.solutions/dashboard', consultant_number: str = None):
        """04 — Welcome email after registration."""
        consultant_number_block = ""
        if consultant_number:
            consultant_number_block = f"<div style='margin: 20px 0; padding: 15px; background-color: #0A1F30; border-left: 4px solid #0EC277; border-radius: 4px;'><p style='margin: 0; color: #ffffff;'>Your Consultant ID is: <strong style='color: #0EC277; font-size: 18px;'>{consultant_number}</strong></p><p style='margin: 5px 0 0 0; font-size: 13px; color: #94a3b8;'>Please keep this ID safe as you will need it for verification.</p></div>"

        html = cls._render('04-welcome-email.html', {
            'dashboard_url': dashboard_url,
            'consultant_number_block': consultant_number_block,
        })
        return cls._send('Welcome to ORR Solutions!', recipient_email, html)

    @classmethod
    def send_onboarding_completion(cls, recipient_email: str, user_name: str,
                                   workspace_url: str = 'https://orr.solutions/workspace'):
        """05 — Onboarding profile submitted."""
        html = cls._render('05-onboarding-completion.html', {
            'user_name': user_name,
            'workspace_url': workspace_url,
        })
        return cls._send('Onboarding Complete - ORR Solutions', recipient_email, html)

    @classmethod
    def send_workspace_setup(cls, recipient_email: str, workspace_url: str,
                             workspace_email: str, storage_limit: str = '5 GB'):
        """06 — Workspace provisioned."""
        html = cls._render('06-workspace-setup.html', {
            'workspace_url': workspace_url,
            'workspace_email': workspace_email,
            'storage_limit': storage_limit,
        })
        return cls._send('Your Workspace is Ready - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 2. WORKFLOW & TICKETS
    # ──────────────────────────────────────────────

    @classmethod
    def send_form_confirmation(cls, recipient_email: str, form_name: str, reference_id: str,
                               submission_date: str, summary_text: str, tracking_link: str):
        """07 — Form/ticket submission confirmation to client."""
        html = cls._render('07-form-confirmation.html', {
            'form_name': form_name,
            'reference_id': reference_id,
            'submission_date': submission_date,
            'summary_text': summary_text,
            'tracking_link': tracking_link,
        })
        return cls._send(f'Submission Confirmed: {form_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_admin_notification(cls, recipient_emails: list, submitter_name: str,
                                submitter_email: str, form_name: str, reference_id: str,
                                admin_link: str):
        """08 — Notify admin of new client submission/message."""
        html = cls._render('08-admin-notification.html', {
            'submitter_name': submitter_name,
            'submitter_email': submitter_email,
            'form_name': form_name,
            'reference_id': reference_id,
            'admin_link': admin_link,
        })
        return cls._send(f'New Submission: {form_name} ({reference_id})', recipient_emails, html)

    @classmethod
    def send_status_update(cls, recipient_email: str, form_name: str, reference_id: str,
                           current_status: str, progress_percentage: str, tracking_link: str):
        """09 — Status update notification to client."""
        html = cls._render('09-status-update.html', {
            'form_name': form_name,
            'reference_id': reference_id,
            'current_status': current_status,
            'progress_percentage': progress_percentage,
            'tracking_link': tracking_link,
        })
        return cls._send(f'Status Update: {form_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_action_required(cls, recipient_email: str, form_name: str, reference_id: str,
                             missing_info_detail: str, action_link: str):
        """10 — Action required / escalation."""
        html = cls._render('10-action-required.html', {
            'form_name': form_name,
            'reference_id': reference_id,
            'missing_info_detail': missing_info_detail,
            'action_link': action_link,
        })
        return cls._send(f'Action Required: {form_name} - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 3. DOCUMENT VAULT
    # ──────────────────────────────────────────────

    @classmethod
    def send_document_generated(cls, recipient_email: str, document_name: str, document_url: str):
        """11 — Document generated."""
        html = cls._render('11-document-generated.html', {
            'document_name': document_name,
            'document_url': document_url,
        })
        return cls._send(f'Document Ready: {document_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_document_review(cls, recipient_email: str, document_name: str,
                             author_name: str, review_url: str):
        """12 — Document submitted for review."""
        html = cls._render('12-document-review.html', {
            'document_name': document_name,
            'author_name': author_name,
            'review_url': review_url,
        })
        return cls._send(f'Document Review Needed: {document_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_document_approved(cls, recipient_email: str, document_name: str,
                               document_url: str, folder_path: str = 'Document Vault'):
        """13 — Document approved."""
        html = cls._render('13-document-approved.html', {
            'document_name': document_name,
            'document_url': document_url,
            'folder_path': folder_path,
        })
        return cls._send(f'Document Approved: {document_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_document_rejected(cls, recipient_email: str, document_name: str,
                               reviewer_comments: str, edit_url: str):
        """14 — Document rejected / revisions needed."""
        html = cls._render('14-document-rejected.html', {
            'document_name': document_name,
            'reviewer_comments': reviewer_comments,
            'edit_url': edit_url,
        })
        return cls._send(f'Revisions Required: {document_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_document_access(cls, recipient_email: str, document_name: str, sharer_name: str,
                             permission_level: str, document_url: str, personal_note: str = ''):
        """15 — Document access shared."""
        html = cls._render('15-document-access.html', {
            'document_name': document_name,
            'sharer_name': sharer_name,
            'permission_level': permission_level,
            'document_url': document_url,
            'personal_note': personal_note,
        })
        return cls._send(f'Document Shared: {document_name} - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 4. PAYMENTS & BILLING
    # ──────────────────────────────────────────────

    @classmethod
    def send_payment_success(cls, recipient_email: str, invoice_id: str, amount_paid: str,
                             currency_symbol: str, payment_date: str, payment_method: str,
                             invoice_url: str):
        """16 — Payment successful."""
        html = cls._render('16-payment-success.html', {
            'invoice_id': invoice_id,
            'amount_paid': amount_paid,
            'currency_symbol': currency_symbol,
            'payment_date': payment_date,
            'payment_method': payment_method,
            'invoice_url': invoice_url,
        })
        return cls._send('Payment Confirmed - ORR Solutions', recipient_email, html)

    @classmethod
    def send_payment_failed(cls, recipient_email: str, invoice_id: str,
                            failure_reason: str, update_payment_url: str):
        """17 — Payment failed."""
        html = cls._render('17-payment-failed.html', {
            'invoice_id': invoice_id,
            'failure_reason': failure_reason,
            'update_payment_url': update_payment_url,
        })
        return cls._send('Payment Failed - ORR Solutions', recipient_email, html)

    @classmethod
    def send_invoice_generated(cls, recipient_email: str, invoice_id: str, total_amount: str,
                               currency_symbol: str, due_date: str, pay_invoice_url: str):
        """18 — Invoice generated."""
        html = cls._render('18-invoice-generated.html', {
            'invoice_id': invoice_id,
            'total_amount': total_amount,
            'currency_symbol': currency_symbol,
            'due_date': due_date,
            'pay_invoice_url': pay_invoice_url,
        })
        return cls._send(f'Invoice #{invoice_id} Generated - ORR Solutions', recipient_email, html)

    @classmethod
    def send_invoice_reminder(cls, recipient_email: str, invoice_id: str, amount_due: str,
                              currency_symbol: str, due_date: str, days_left: str,
                              pay_invoice_url: str):
        """19 — Invoice payment reminder."""
        html = cls._render('19-invoice-reminder.html', {
            'invoice_id': invoice_id,
            'amount_due': amount_due,
            'currency_symbol': currency_symbol,
            'due_date': due_date,
            'days_left': days_left,
            'pay_invoice_url': pay_invoice_url,
        })
        return cls._send(f'Payment Reminder: Invoice #{invoice_id} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_subscription_update(cls, recipient_email: str, old_plan_name: str,
                                 new_plan_name: str, billing_portal_url: str):
        """20 — Subscription plan changed."""
        html = cls._render('20-subscription-update.html', {
            'old_plan_name': old_plan_name,
            'new_plan_name': new_plan_name,
            'billing_portal_url': billing_portal_url,
        })
        return cls._send('Subscription Updated - ORR Solutions', recipient_email, html)

    @classmethod
    def send_wallet_topup(cls, recipient_email: str, transaction_id: str, added_amount: str,
                          currency_symbol: str, new_balance: str, wallet_url: str):
        """21 — Wallet top-up confirmation."""
        html = cls._render('21-wallet-topup.html', {
            'transaction_id': transaction_id,
            'added_amount': added_amount,
            'currency_symbol': currency_symbol,
            'new_balance': new_balance,
            'wallet_url': wallet_url,
        })
        return cls._send('Wallet Top-Up Confirmed - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 5. CONSULTANT WORKFLOW
    # ──────────────────────────────────────────────

    @classmethod
    def send_task_assignment(cls, recipient_email: str, consultant_name: str, task_name: str,
                            task_description: str, project_name: str, priority_level: str,
                            due_date: str, task_url: str):
        """22 — Task assigned to consultant."""
        html = cls._render('22-task-assignment.html', {
            'consultant_name': consultant_name,
            'task_name': task_name,
            'task_description': task_description,
            'project_name': project_name,
            'priority_level': priority_level,
            'due_date': due_date,
            'task_url': task_url,
        })
        return cls._send(f'New Task Assigned: {task_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_task_reminder(cls, recipient_email: str, task_name: str, due_date: str,
                           time_remaining: str, task_url: str):
        """23 — Task deadline reminder."""
        html = cls._render('23-task-reminder.html', {
            'task_name': task_name,
            'due_date': due_date,
            'time_remaining': time_remaining,
            'task_url': task_url,
        })
        return cls._send(f'Task Reminder: {task_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_task_completion(cls, recipient_email: str, task_name: str, submission_id: str,
                            submission_date: str, task_status_url: str):
        """24 — Task completed."""
        html = cls._render('24-task-completion.html', {
            'task_name': task_name,
            'submission_id': submission_id,
            'submission_date': submission_date,
            'task_status_url': task_status_url,
        })
        return cls._send(f'Task Completed: {task_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_consultant_invoice_confirm(cls, recipient_email: str, consultant_name: str,
                                        invoice_id: str, invoice_amount: str,
                                        currency_symbol: str, billing_period: str,
                                        payout_dashboard_url: str):
        """25 — Consultant invoice uploaded confirmation."""
        html = cls._render('25-consultant-invoice-confirm.html', {
            'consultant_name': consultant_name,
            'invoice_id': invoice_id,
            'invoice_amount': invoice_amount,
            'currency_symbol': currency_symbol,
            'billing_period': billing_period,
            'payout_dashboard_url': payout_dashboard_url,
        })
        return cls._send(f'Invoice #{invoice_id} Received - ORR Solutions', recipient_email, html)

    @classmethod
    def send_consultant_invoice_status(cls, recipient_email: str, invoice_id: str,
                                       invoice_amount: str, currency_symbol: str,
                                       status_label: str, status_color: str,
                                       status_border_color: str, status_timestamp: str,
                                       reviewer_feedback: str, feedback_display: str,
                                       cta_label: str, action_url: str):
        """26 — Consultant invoice status update."""
        html = cls._render('26-consultant-invoice-status.html', {
            'invoice_id': invoice_id,
            'invoice_amount': invoice_amount,
            'currency_symbol': currency_symbol,
            'status_label': status_label,
            'status_color': status_color,
            'status_border_color': status_border_color,
            'status_timestamp': status_timestamp,
            'reviewer_feedback': reviewer_feedback,
            'feedback_display': feedback_display,
            'cta_label': cta_label,
            'action_url': action_url,
        })
        return cls._send(f'Invoice #{invoice_id} Status Update - ORR Solutions', recipient_email, html)

    @classmethod
    def send_consultant_payout(cls, recipient_email: str, payout_id: str, payout_amount: str,
                               currency_symbol: str, payout_method: str, payout_history_url: str):
        """27 — Consultant payout processed."""
        html = cls._render('27-consultant-payout.html', {
            'payout_id': payout_id,
            'payout_amount': payout_amount,
            'currency_symbol': currency_symbol,
            'payout_method': payout_method,
            'payout_history_url': payout_history_url,
        })
        return cls._send('Payout Processed - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 6. MEETINGS & SCHEDULING
    # ──────────────────────────────────────────────

    @classmethod
    def send_meeting_scheduled(cls, recipient_email: str, meeting_subject: str,
                               meeting_time: str, meeting_link: str):
        """28 — Meeting scheduled/confirmed."""
        html = cls._render('28-meeting-scheduled.html', {
            'meeting_subject': meeting_subject,
            'meeting_time': meeting_time,
            'meeting_link': meeting_link,
        })
        return cls._send(f'Meeting Scheduled: {meeting_subject} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_meeting_reminder(cls, recipient_email: str, meeting_subject: str,
                              meeting_time: str, minutes_until: str, meeting_link: str):
        """29 — Meeting reminder."""
        html = cls._render('29-meeting-reminder.html', {
            'meeting_subject': meeting_subject,
            'meeting_time': meeting_time,
            'minutes_until': minutes_until,
            'meeting_link': meeting_link,
        })
        return cls._send(f'Meeting Reminder: {meeting_subject} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_host_joined(cls, recipient_email: str, meeting_subject: str, meeting_link: str):
        """29b — Host joined notification."""
        html = cls._render('29b-host-joined.html', {
            'meeting_subject': meeting_subject,
            'meeting_link': meeting_link,
        })
        return cls._send(f'Host has joined: {meeting_subject} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_meeting_rescheduled(cls, recipient_email: str, meeting_subject: str,
                                 old_time: str, new_time: str, meeting_link: str):
        """30 — Meeting rescheduled."""
        html = cls._render('30-meeting-rescheduled.html', {
            'meeting_subject': meeting_subject,
            'old_time': old_time,
            'new_time': new_time,
            'meeting_link': meeting_link,
        })
        return cls._send(f'Meeting Rescheduled: {meeting_subject} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_meeting_cancelled(cls, recipient_email: str, meeting_subject: str,
                               meeting_time: str, cancellation_reason: str,
                               scheduling_url: str = 'https://orr.solutions/meetings'):
        """31 — Meeting cancelled."""
        html = cls._render('31-meeting-cancelled.html', {
            'meeting_subject': meeting_subject,
            'meeting_time': meeting_time,
            'cancellation_reason': cancellation_reason,
            'scheduling_url': scheduling_url,
        })
        return cls._send(f'Meeting Cancelled: {meeting_subject} - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 7. SYSTEM & SECURITY
    # ──────────────────────────────────────────────

    @classmethod
    def send_system_error(cls, recipient_email: str, workflow_id: str, error_message: str,
                          error_timestamp: str, error_logs_url: str):
        """32 — System error alert."""
        html = cls._render('32-system-error.html', {
            'workflow_id': workflow_id,
            'error_message': error_message,
            'error_timestamp': error_timestamp,
            'error_logs_url': error_logs_url,
        })
        return cls._send('⚠️ System Error Alert - ORR Solutions', recipient_email, html)

    @classmethod
    def send_webhook_failure(cls, recipient_email: str, source_service: str,
                             endpoint_url: str, payload_json: str):
        """33 — Webhook failure."""
        html = cls._render('33-webhook-failure.html', {
            'source_service': source_service,
            'endpoint_url': endpoint_url,
            'payload_json': payload_json,
        })
        return cls._send(f'Webhook Failure: {source_service} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_security_alert(cls, recipient_email: str, activity_type: str, activity_time: str,
                            ip_address: str, activity_location: str, security_review_url: str):
        """34 — Security alert."""
        html = cls._render('34-security-alert.html', {
            'activity_type': activity_type,
            'activity_time': activity_time,
            'ip_address': ip_address,
            'activity_location': activity_location,
            'security_review_url': security_review_url,
        })
        return cls._send('🔒 Security Alert - ORR Solutions', recipient_email, html)

    @classmethod
    def send_access_revoked(cls, recipient_email: str, workspace_name: str,
                            revocation_reason: str, revocation_date: str,
                            help_center_url: str = 'https://orr.solutions/support'):
        """35 — Access revoked."""
        html = cls._render('35-access-revoked.html', {
            'workspace_name': workspace_name,
            'revocation_reason': revocation_reason,
            'revocation_date': revocation_date,
            'help_center_url': help_center_url,
        })
        return cls._send('Access Revoked - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 8. ADMIN & GOVERNANCE
    # ──────────────────────────────────────────────

    @classmethod
    def send_admin_approval_request(cls, recipient_email: str, action_name: str,
                                    initiator_name: str, risk_level: str,
                                    action_description: str, approve_url: str, deny_url: str):
        """36 — Admin approval request."""
        html = cls._render('36-admin-approval-request.html', {
            'action_name': action_name,
            'initiator_name': initiator_name,
            'risk_level': risk_level,
            'action_description': action_description,
            'approve_url': approve_url,
            'deny_url': deny_url,
        })
        return cls._send(f'Approval Required: {action_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_admin_approval_status(cls, recipient_email: str, action_name: str, request_id: str,
                                   decision_label: str, decision_time: str,
                                   reviewer_comments: str, status_color: str,
                                   action_log_url: str):
        """37 — Admin approval decision."""
        html = cls._render('37-admin-approval-status.html', {
            'action_name': action_name,
            'request_id': request_id,
            'decision_label': decision_label,
            'decision_time': decision_time,
            'reviewer_comments': reviewer_comments,
            'status_color': status_color,
            'action_log_url': action_log_url,
        })
        return cls._send(f'Approval Decision: {action_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_role_change_notification(cls, recipient_email: str, workspace_name: str,
                                      new_role_name: str, role_description: str,
                                      dashboard_url: str = 'https://orr.solutions/dashboard'):
        """38 — Role change notification."""
        html = cls._render('38-role-change-notification.html', {
            'workspace_name': workspace_name,
            'new_role_name': new_role_name,
            'role_description': role_description,
            'dashboard_url': dashboard_url,
        })
        return cls._send('Role Updated - ORR Solutions', recipient_email, html)

    # ──────────────────────────────────────────────
    # 9. MARKETING & ENGAGEMENT
    # ──────────────────────────────────────────────

    @classmethod
    def send_newsletter(cls, recipient_email: str, post_title: str, post_excerpt: str,
                        post_category: str, author_name: str, read_time: str,
                        post_hero_url: str, post_url: str,
                        unsubscribe_url: str = 'https://orr.solutions/unsubscribe'):
        """39 — Newsletter / blog update."""
        html = cls._render('39-newsletter-blog-update.html', {
            'post_title': post_title,
            'post_excerpt': post_excerpt,
            'post_category': post_category,
            'author_name': author_name,
            'read_time': read_time,
            'post_hero_url': post_hero_url,
            'post_url': post_url,
            'unsubscribe_url': unsubscribe_url,
        })
        return cls._send(f'{post_title} - ORR Solutions Blog', recipient_email, html)

    @classmethod
    def send_feature_announcement(cls, recipient_email: str, feature_name: str,
                                  feature_brief: str, feature_screenshot_url: str,
                                  try_now_url: str, changelog_url: str):
        """40 — Feature announcement."""
        html = cls._render('40-feature-announcement.html', {
            'feature_name': feature_name,
            'feature_brief': feature_brief,
            'feature_screenshot_url': feature_screenshot_url,
            'try_now_url': try_now_url,
            'changelog_url': changelog_url,
        })
        return cls._send(f'New Feature: {feature_name} - ORR Solutions', recipient_email, html)

    @classmethod
    def send_reengagement(cls, recipient_email: str, user_name: str,
                          dashboard_url: str = 'https://orr.solutions/dashboard'):
        """41 — Re-engagement for inactive users."""
        html = cls._render('41-reengagement-alert.html', {
            'user_name': user_name,
            'dashboard_url': dashboard_url,
        })
        return cls._send('We Miss You! - ORR Solutions', recipient_email, html)
