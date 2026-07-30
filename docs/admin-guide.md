# ORR Solutions Comprehensive Admin Guide

This guide details the administrative operations, configuration workflows, and security procedures for the ORR Solutions platform.

## 1. Role Management & Access Control
Access to the Admin Portal is strictly governed by `AdminRole` records.
- **Super Admin**: Bypasses most checks. Has full access to System Configuration, Security Audit Logs, and destructive actions.
- **Admin**: Standard administrative access. Can manage users, clients, and approve most workflows.
- **Content Editor**: Restricted to CMS and content modification endpoints.
- **Operator/Support**: Restricted to ticketing, meeting scheduling, and front-line support queries.

**Adding a New Admin**: Create a new User via the Django Admin interface, assign them an `AdminProfile`, and select the appropriate `AdminRole`.

## 2. System Configuration
Located under Settings > Security in the Admin Dashboard, the `SystemConfig` module controls global security flags:
- **MFA Enforced Roles**: A configurable list (e.g., `["admin", "consultant", "pm"]`) dictating which user roles must use TOTP. If `["all"]` is specified, it enforces MFA globally.
- **IP Bounds Restricted**: When enabled, the backend will reject requests from IPs not explicitly whitelisted.
- **Maintenance Mode**: Disables all public and client-facing endpoints with a 503 response, allowing only Super Admins to log in.
- **Session Timeout**: Configures the duration of inactivity before a JWT is forcefully expired (default `1h`).

## 3. Security Audit Logs
All security-relevant actions (login, logout, system config changes, manual backups) are logged to the `SecurityAuditLog`.
- Logs are strictly append-only.
- Logs include `user_email`, `ip_address`, `user_agent`, and a `metadata` JSON payload.
- Only users with `can_view_audit_logs` (typically Super Admins) can access the Audit Dashboard.

## 4. Approval Queue (Dual-Approval Workflow)
Sensitive actions (e.g., wallet top-ups over a certain threshold, consultant payouts, refund processing) require dual approval.
1. An admin initiates the action. The action is serialized and saved to the `ApprovalQueue` in a `pending` state.
2. A *different* admin with appropriate permissions must review the queue and click "Approve".
3. The system executes the serialized action and updates the queue state to `approved`.

## 5. Wallet & Payment Management
Clients fund a pre-paid `Wallet`.
- **Top-Ups**: Usually handled automatically via Stripe webhooks. Manual top-ups require the Approval Queue.
- **Debits**: PMs and Consultants log hours or deliverables against a project. When approved, funds are debited from the Client's wallet.
- **Zero Balance**: The system automatically halts billable PM workflows if a client's wallet reaches zero.

## 6. PM Project Oversight
While Project Managers (PMs) handle day-to-day operations, Admins have oversight capabilities:
- Admins can re-assign a PM to a `PMProject` if the original PM is unavailable.
- Admins can view the internal `pm_notes` and override workflow states in case of a dispute or edge-case blocker.

## 7. Consultant Approval Workflow
1. A consultant registers and completes the `OnboardingQuestionnaire`.
2. They are placed in `pending_review` status.
3. An Admin reviews their submitted certifications and ID documents via the Vault.
4. The Admin clicks "Approve", shifting their status to `active`, allowing them to view `PMOpportunity` listings.

## 8. Content/CMS Management
The `orr_frontend` (Next.js) relies entirely on backend CMS data.
- Edits made in the Admin Portal CMS immediately affect the frontend.
- Uses `django-modeltranslation` for multilingual support. Content Editors must provide translations (e.g., EN, IT) before publishing.
- **Publish Workflow**: Changes can be saved as `Draft`. Only when marked `Published` will the API expose them to the public frontend.

## 9. Backup & Restore Procedures
- **Automated Backups**: Celery runs `backup_database_daily` and `backup_workspace_weekly`.
- **Manual Backups**: Super Admins can trigger an immediate database snapshot via the System Config dashboard.
- **Restoration**: Refer to `disaster-recovery.md` for CLI commands to decrypt (`gpg --decrypt`) and restore (`psql`) backups from Google Cloud Storage.

## 10. Super Admin Emergency Operations
- **MFA Lockout**: If an admin loses their MFA device, a Super Admin must use the Django Admin interface (`/admin/`) to delete the user's `TOTPDevice` record, forcing them to re-enroll on next login.
- **Suspending Users**: Admins can immediately suspend any non-admin user via the dashboard, instantly invalidating their active sessions.
