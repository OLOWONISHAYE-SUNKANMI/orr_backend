"""
ORR Workflow State Machine

Enforces valid status transitions for all major models.
Any status change not listed in the transition map is rejected.

Usage:
    from common.state_machine import validate_transition
    validate_transition('pm_project', current_status, new_status)
"""

from rest_framework.exceptions import ValidationError


# ═══════════════════════════════════════════════════════════
# TRANSITION MAPS
# Each key maps to a set of valid next-statuses.
# ═══════════════════════════════════════════════════════════

PM_PROJECT_TRANSITIONS = {
    'draft': {'awaiting_client_confirmation', 'pending_admin_review', 'cancelled'},
    'awaiting_client_confirmation': {'awaiting_payment', 'pending_admin_review', 'cancelled', 'draft'},
    'awaiting_payment': {'pending_admin_review', 'cancelled'},
    'pending_admin_review': {
        'needs_pm_clarification', 'approved_for_sourcing', 'cancelled', 'on_hold',
    },
    'needs_pm_clarification': {'pending_admin_review', 'cancelled'},
    'approved_for_sourcing': {'ready_for_matching', 'sourcing_internally', 'sourcing_externally', 'cancelled', 'on_hold'},
    'ready_for_matching': {'sourcing_internally', 'sourcing_externally', 'cancelled', 'on_hold'},
    'sourcing_internally': {'consultant_assignment_pending', 'sourcing_externally', 'cancelled', 'on_hold'},
    'sourcing_externally': {'consultant_assignment_pending', 'cancelled', 'on_hold'},
    'consultant_assignment_pending': {'active', 'cancelled', 'on_hold'},
    'active': {'internal_review', 'delivered', 'on_hold', 'cancelled'},
    'internal_review': {'active', 'delivered', 'on_hold'},
    'delivered': {'completed', 'active'},
    'completed': {'closed'},
    'closed': {'archived'},
    'on_hold': {
        'draft', 'pending_admin_review', 'approved_for_sourcing',
        'active', 'cancelled',
    },
    'cancelled': set(),  # Terminal state
    'archived': set(),   # Terminal state
}

CLIENT_REQUEST_TRANSITIONS = {
    'draft': {'submitted', 'archived'},
    'submitted': {'pending_orr_review', 'archived'},
    'pending_orr_review': {
        'clarification_requested', 'approved_for_meeting',
        'approved_for_pm_assignment', 'rejected', 'archived',
    },
    'clarification_requested': {'pending_orr_review', 'archived'},
    'approved_for_meeting': {'converted_to_project', 'closed', 'archived'},
    'approved_for_pm_assignment': {'converted_to_project', 'closed', 'archived'},
    'converted_to_project': {'closed', 'archived'},
    'rejected': {'archived'},
    'closed': {'archived'},
    'archived': set(),  # Terminal state
}

MEETING_TRANSITIONS = {
    'requested': {'confirmed', 'declined', 'cancelled', 'rescheduled'},
    'confirmed': {'completed', 'cancelled', 'rescheduled'},
    'rescheduled': {'confirmed', 'declined', 'cancelled'},
    'declined': set(),    # Terminal state
    'completed': set(),   # Terminal state
    'cancelled': set(),   # Terminal state
}

CONTENT_TRANSITIONS = {
    'draft': {'published'},
    'published': {'draft', 'archived'},
    'archived': {'draft'},
}

TICKET_TRANSITIONS = {
    'new': {'processing', 'resolved', 'archived'},
    'processing': {'payment_failed', 'payment_disputed', 'resolved', 'archived'},
    'payment_failed': {'processing', 'refund_requested', 'resolved', 'archived'},
    'payment_disputed': {'refund_requested', 'resolved', 'archived'},
    'refund_requested': {'refund_processed', 'resolved', 'archived'},
    'refund_processed': {'resolved', 'archived'},
    'resolved': {'archived'},
    'archived': set(),  # Terminal state
}

# PM Task transitions
PM_TASK_TRANSITIONS = {
    'draft': {'not_started', 'in_progress', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'awaiting_assignment', 'awaiting_client_input', 'on_hold'},
    'not_started': {'draft', 'in_progress', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'awaiting_assignment', 'awaiting_client_input', 'on_hold'},
    'awaiting_assignment': {'draft', 'not_started', 'in_progress', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'awaiting_client_input', 'on_hold'},
    'awaiting_client_input': {'draft', 'not_started', 'awaiting_assignment', 'in_progress', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'on_hold'},
    'in_progress': {'draft', 'not_started', 'awaiting_assignment', 'awaiting_client_input', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'on_hold', 'revision_required'},
    'blocked': {'draft', 'not_started', 'awaiting_assignment', 'awaiting_client_input', 'in_progress', 'submitted_for_review', 'completed', 'cancelled', 'on_hold'},
    'submitted_for_review': {'draft', 'not_started', 'awaiting_assignment', 'awaiting_client_input', 'in_progress', 'blocked', 'completed', 'cancelled', 'on_hold', 'revision_required'},
    'revision_required': {'draft', 'not_started', 'awaiting_assignment', 'awaiting_client_input', 'in_progress', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'on_hold'},
    'on_hold': {'draft', 'not_started', 'awaiting_assignment', 'awaiting_client_input', 'in_progress', 'blocked', 'submitted_for_review', 'completed', 'cancelled', 'revision_required'},
    'completed': {'not_started', 'in_progress'}, # Allow reopening
    'cancelled': {'not_started', 'in_progress'}, # Allow reopening
    'closed': set(),
}

# Consultant assignment transitions
PM_ASSIGNMENT_TRANSITIONS = {
    'draft': {'proposed', 'invitation_sent', 'access_activated', 'cancelled'},
    'proposed': {'invitation_sent', 'access_activated', 'cancelled'},
    'invitation_sent': {'pending_consultant_response', 'accepted', 'declined', 'access_activated', 'cancelled'},
    'pending_consultant_response': {'accepted', 'declined', 'needs_clarification', 'expired'},
    'accepted': {'conflict_review_required', 'access_activated', 'suspended', 'cancelled', 'withdrawn'},
    'conflict_review_required': {'access_activated', 'suspended', 'cancelled'},
    'access_activated': {'active', 'suspended', 'cancelled', 'withdrawn'},
    'active': {'completed', 'suspended', 'cancelled', 'withdrawn'},
    'completed': set(),
    'declined': set(),
    'cancelled': set(),
    'withdrawn': set(),
    'suspended': {'active', 'cancelled'},
    'needs_clarification': {'invitation_sent', 'cancelled', 'expired'},
    'expired': set(),
    'pending_acceptance': {'accepted', 'declined'},
}

# ═══════════════════════════════════════════════════════════
# MODEL → TRANSITION MAP REGISTRY
# ═══════════════════════════════════════════════════════════

TRANSITION_REGISTRY = {
    'pm_project': PM_PROJECT_TRANSITIONS,
    'client_request': CLIENT_REQUEST_TRANSITIONS,
    'meeting': MEETING_TRANSITIONS,
    'content': CONTENT_TRANSITIONS,
    'ticket': TICKET_TRANSITIONS,
    'pm_task': PM_TASK_TRANSITIONS,
    'pm_assignment': PM_ASSIGNMENT_TRANSITIONS,
}


def validate_transition(model_key: str, current_status: str, new_status: str) -> None:
    """
    Validate that a status transition is allowed.

    Args:
        model_key: Key from TRANSITION_REGISTRY (e.g., 'pm_project')
        current_status: The current status value
        new_status: The desired new status value

    Raises:
        ValidationError: If the transition is not allowed.
    """
    # Same status → no-op, always allowed
    if current_status == new_status:
        return

    transition_map = TRANSITION_REGISTRY.get(model_key)
    if transition_map is None:
        # Unknown model key — skip validation to avoid breaking unknown workflows
        return

    valid_next = transition_map.get(current_status)
    if valid_next is None:
        raise ValidationError(
            f"Unknown current status '{current_status}' for {model_key}."
        )

    if new_status not in valid_next:
        allowed = ', '.join(sorted(valid_next)) if valid_next else '(none — terminal state)'
        raise ValidationError(
            f"Invalid status transition for {model_key}: "
            f"'{current_status}' → '{new_status}' is not allowed. "
            f"Valid transitions from '{current_status}': {allowed}"
        )


class StateMachineMixin:
    """
    Mixin to automatically validate status transitions on save().
    Models using this must define `STATE_MACHINE_MODEL_KEY` (e.g., 'pm_project').
    """
    STATE_MACHINE_MODEL_KEY = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = getattr(self, 'status', None)

    def save(self, *args, **kwargs):
        if self.pk and self.STATE_MACHINE_MODEL_KEY:
            current_status = getattr(self, 'status', None)
            if current_status and self._original_status and current_status != self._original_status:
                validate_transition(self.STATE_MACHINE_MODEL_KEY, self._original_status, current_status)
        super().save(*args, **kwargs)
        self._original_status = getattr(self, 'status', None)
