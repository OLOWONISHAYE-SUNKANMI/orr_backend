from django.test import TestCase
from common.state_machine import validate_transition
from rest_framework.exceptions import ValidationError

class StateMachineTestCase(TestCase):
    def test_valid_transition(self):
        # planning -> approved is valid
        try:
            validate_transition('pm_project', 'draft', 'awaiting_client_confirmation')
        except ValidationError:
            self.fail("Valid transition raised ValidationError")

    def test_invalid_transition(self):
        # planning -> in_progress is invalid directly
        with self.assertRaises(ValidationError):
            validate_transition('pm_project', 'draft', 'completed')

    def test_terminal_state(self):
        # closed -> anything is invalid
        with self.assertRaises(ValidationError):
            validate_transition('pm_project', 'closed', 'planning')

    def test_same_state(self):
        # Same state should always be valid
        try:
            validate_transition('pm_project', 'planning', 'planning')
        except ValidationError:
            self.fail("Same state transition raised ValidationError")
