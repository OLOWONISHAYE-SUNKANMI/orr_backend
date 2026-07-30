# ORR Solutions API Documentation

This document provides a comprehensive overview of the ORR backend APIs.
The platform uses a modular DRF (Django Rest Framework) architecture, with endpoints logically grouped by the actor (Client, Admin, Consultant, PM) or the feature domain (Payment, Auth, Core).

**Note:** A complete, interactive OpenAPI schema is automatically generated via `drf-spectacular` and is available in the development and staging environments at:
- Swagger UI: `GET /api/schema/swagger-ui/`
- Redoc: `GET /api/schema/redoc/`
- Schema JSON/YAML: `GET /api/schema/`

## 1. Authentication & MFA
Authentication is handled via JWT (JSON Web Tokens). Endpoints are prefixed with `/api/auth/`.

- `POST /api/auth/login/` - Authenticates user. Returns `access` and `refresh` tokens. If MFA is required for the user's role, the token will lack the `mfa_verified` claim.
- `POST /api/auth/mfa/verify/` - Verifies a TOTP code and returns a new JWT with `mfa_verified=True`.
- `POST /api/auth/mfa/setup/` - Generates a new TOTP secret and returns a QR code URL for configuring Authenticator apps.
- `POST /api/auth/refresh/` - Refreshes the JWT token.
- `POST /api/auth/logout/` - Blacklists the token and triggers the logout audit trail.

## 2. Client Portal API (`/api/v1/client/`)
Endpoints used by the Client Dashboard frontend (`http://localhost:3003`).

### Requests & Discovery
- `GET /api/v1/client/requests/` - List all consulting requests for the authenticated client.
- `POST /api/v1/client/requests/` - Create a new consulting request.
- `GET /api/v1/client/requests/<id>/` - Retrieve request details.
- `PATCH /api/v1/client/requests/<id>/` - Update a draft request.

### Profile & Settings
- `GET /api/v1/client/profile/` - Retrieve client profile and onboarding status.
- `PATCH /api/v1/client/profile/` - Update profile information.
- `GET /api/v1/client/activities/` - Retrieve activity feed.

## 3. Admin Portal API (`/admin-portal/v1/`)
Extensive administrative API for the Admin Dashboard (`http://localhost:3000`). Access is heavily controlled by the `AdminRole` permissions.

### System & Security
- `GET /admin-portal/v1/system/config/` - Fetch security flags (MFA roles, IP restrictions, maintenance mode).
- `POST /admin-portal/v1/system/config/` - Update security flags. Requires `can_configure_system`.
- `POST /admin-portal/v1/system/backup/` - Trigger an immediate database backup.
- `GET /admin-portal/v1/audit/logs/` - List structured security event logs. Requires `can_view_audit_logs`.
- `GET /admin-portal/v1/audit/sessions/` - View active admin sessions.

### Client Management
- `GET /admin-portal/v1/clients/` - List all clients.
- `GET /admin-portal/v1/clients/<id>/` - Retrieve client details and history.
- `PATCH /admin-portal/v1/clients/<id>/` - Update client information.

### CMS & Content
- `GET /admin-portal/v1/cms/pages/` - List CMS pages.
- `POST /admin-portal/v1/cms/pages/` - Create a new page. Requires `can_create_content`.
- `PATCH /admin-portal/v1/cms/pages/<id>/publish/` - Publish content. Requires `can_publish_content`.

### Ticketing & Support
- `GET /admin-portal/v1/tickets/` - List support tickets.
- `POST /admin-portal/v1/tickets/<id>/reply/` - Add a message to a ticket.
- `PATCH /admin-portal/v1/tickets/<id>/status/` - Resolve or escalate a ticket.

### Approval Queue
- `GET /admin-portal/v1/approvals/` - List items requiring dual approval.
- `POST /admin-portal/v1/approvals/<id>/approve/` - Approve an action.
- `POST /admin-portal/v1/approvals/<id>/reject/` - Reject an action.

## 4. Consultant Portal API (`/api/v1/consultants/`)
Endpoints used by the Consultant Dashboard frontend (`http://localhost:3001`).

- `GET /api/v1/consultants/<id>/profile/` - Retrieves consultant profile.
- `PATCH /api/v1/consultants/<id>/profile/` - Updates consultant profile.
- `GET /api/v1/consultants/<id>/opportunities/` - Retrieves available assignments.
- `POST /api/v1/consultants/opportunities/<id>/apply/` - Apply for an assignment.

## 5. Project Manager API (`/api/v1/pm/`)
Endpoints for PMs to oversee projects, tasks, and assignments (`http://localhost:3002`).

- `GET /api/v1/pm/projects/` - Lists active and pending projects.
- `POST /api/v1/pm/projects/` - Creates a new project from an approved client request.
- `GET /api/v1/pm/projects/<id>/` - Retrieve project details.
- `PATCH /api/v1/pm/projects/<id>/status/` - Updates project state in the workflow (validates against state machine).
- `GET /api/v1/pm/tasks/` - List tasks across managed projects.
- `POST /api/v1/pm/tasks/` - Create a task and assign to a consultant.

## 6. Payments & Billing (`/api/v1/payment/`)
Financial operations, Stripe integration, and wallet management.

- `GET /api/v1/payment/wallet/` - Retrieve current wallet balance.
- `POST /api/v1/payment/wallet/topup/` - Initiate a top-up (creates Stripe Checkout Session).
- `GET /api/v1/payment/invoices/` - List past and upcoming invoices.
- `POST /api/v1/payment/webhook/` - Stripe webhook endpoint.

---
**Standard Response Formats**
Most endpoints return standardized JSON:
- `200 OK`: `{"data": {...}, "message": "Success"}`
- `400 Bad Request`: `{"error": "Validation failed", "details": {"field": ["Error message"]}}`
- `401 Unauthorized`: `{"error": "Authentication required or MFA missing"}`
- `403 Forbidden`: `{"error": "You do not have permission to perform this action"}`
