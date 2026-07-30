# ORR Platform UAT Checklist

This document is to be utilized during the final User Acceptance Testing (UAT) sign-off phase.

## Pre-Requisites
- [ ] Staging environment deployed with production-like anonymized data.
- [ ] Test accounts created for all roles: `Super Admin`, `Admin`, `Consultant`, `Project Manager`, `Client`, and `QA Tester`.

## 1. Authentication & Security (MFA)
- [ ] Verify standard Email + Password login works for clients and consultants.
- [ ] Verify Google Single Sign-On (SSO) works for clients and consultants.
- [ ] Verify that an Admin account with MFA enforced cannot bypass the 2FA requirement.
- [ ] Setup TOTP using Google Authenticator and verify the 6-digit code grants access.
- [ ] Verify that 1 hour of browser inactivity automatically invalidates the JWT session and redirects to `/login`.

## 2. Dual-Approval & Concurrency
- [ ] Login as `Super Admin A` and `Super Admin B`.
- [ ] Both admins attempt to approve the *same* `Content` item at the exact same moment.
- [ ] Verify that race conditions do not occur (one admin receives a "success", the other receives an "already processed" or similar state transition error).
- [ ] Verify the transaction log records only one approval action.

## 3. Financial Edge Cases
- [ ] Login as a `Client`.
- [ ] Attempt to trigger a wallet deduction (e.g., confirming a milestone) when the wallet balance is $0.
- [ ] Verify the system throws a strict "Insufficient funds" validation error, and the database transaction rolls back cleanly without negative balances.

## 4. Workflow State Machine
- [ ] Transition a `PMProject` from `planning` to `approved`.
- [ ] Attempt to transition a `PMProject` directly from `planning` to `closed` (Invalid Transition).
- [ ] Verify the system rejects the invalid transition based on `TRANSITION_REGISTRY`.

## 5. Audit Logging
- [ ] Perform a CRUD action (Create a Ticket, Edit a Meeting, Delete a Content piece).
- [ ] Login as `Super Admin`.
- [ ] Navigate to the Audit Center and verify that all `post_save` and `post_delete` signals successfully captured the user ID, timestamp, and changes.

## 6. Disaster Recovery 
- [ ] Run the database backup task manually.
- [ ] Verify the `.sql.gz` file exists in the GCS bucket.
- [ ] Delete a non-critical piece of data in the staging UI.
- [ ] Execute `restore_db.sh`.
- [ ] Verify the deleted data is restored in the staging UI.

## Sign Off
**QA Tester Signature:** ______________________  **Date:** _________
**ORR Stakeholder Signature:** ______________________  **Date:** _________
