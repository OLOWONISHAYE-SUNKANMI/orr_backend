# ORR Solutions Support & Maintenance SLA

**Effective Date:** 14 July 2026
**Duration:** 6 Months (Expires 14 January 2027)

## 1. Overview
This Service Level Agreement (SLA) outlines the terms of support and maintenance provided for the ORR Solutions platform post-UAT sign-off.

## 2. Coverage
- **Bug Fixes:** Resolution of critical, major, and minor defects in the core application logic (Admin, PM, Client, Consultant portals).
- **Security Patches:** Application of critical security updates to Django, React/Next.js, and underlying dependencies.
- **Uptime Monitoring:** Basic oversight of application availability on Google Cloud Platform.
- **Routine Maintenance:** Log rotation, database optimization, and backup verification.

## 3. Exclusions
- **New Feature Development:** Any requests outside the original scope document will be scoped and billed separately.
- **Third-Party Service Outages:** Outages caused by Stripe, Google Workspace, AWS/GCP infrastructure, or Twilio/SendGrid.
- **Data Entry / CMS Content Management:** Adding or modifying marketing content or user data is the responsibility of the ORR Admin team.

## 4. Defect Resolution & Response Times

| Priority Level | Description | Response Time | Target Resolution |
|---|---|---|---|
| **Critical (P1)** | Complete system outage, critical security breach, or inability to process payments. | 2 Hours | 12 Hours |
| **Major (P2)** | Core workflow broken for a significant subset of users, no workaround available. | 8 Hours | 48 Hours |
| **Minor (P3)** | Non-critical bugs, UI glitches, or issues with a viable workaround. | 24 Hours | 7 Days |

*Response times apply during standard business hours (9 AM - 6 PM UTC).*

## 5. Reporting Procedures
All defects must be logged via the designated issue tracking system or by contacting the dedicated support email. Reports must include:
- A clear description of the issue.
- Steps to reproduce.
- Relevant screenshots or error codes.
- The user account/role experiencing the issue.

## 6. Escalation Matrix
If response SLAs are not met, issues can be escalated to:
1. **Primary Developer:** (Contact provided in private handover)
2. **Project Manager:** (Contact provided in private handover)

## 7. Sign-Off
This document constitutes the formal SLA for the 6-month support period following the acceptance of the Final UAT.
