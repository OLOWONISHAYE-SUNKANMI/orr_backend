"""
PM Views
Complete API layer for the PM workflow.
Covers: Projects, Tasks, Consultant Matching, Assignments, Opportunities.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from common.response import api_response
from client.models import Project
from consultation.models import ConsultantJob

class PMRequestConsultantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        # Allow PM to request a consultant for a project
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(api_response(success=False, error="Project not found", status_code=status.HTTP_404_NOT_FOUND))

        scope = request.data.get('scope', [])
        deliverables = request.data.get('deliverables', [])
        title = request.data.get('title', f"Consultant for {project.name}")

        job = ConsultantJob.objects.create(
            project=project,
            title=title,
            industry=project.client.industry if hasattr(project.client, 'industry') else 'Consulting',
            client_sector=project.classification,
            scope=scope,
            deliverables=deliverables,
            status='REQUESTED_BY_PM'
        )

        return Response(api_response(
            success=True,
            message="Consultant request submitted successfully.",
            data={'job_id': job.id}
        ))

def sync_pm_task_to_consultant(pm_task):
    """Helper to sync PMTask status to ConsultantTask when PM updates the task manually."""
    from consultation.models import ConsultantTask, ConsultantJob
    from pm.models import PMAssignment
    STATUS_MAP = {
        'draft': 'NOT_STARTED',
        'not_started': 'NOT_STARTED',
        'awaiting_assignment': 'ASSIGNED',
        'awaiting_client_input': 'ASSIGNED',
        'in_progress': 'IN_PROGRESS',
        'submitted_for_review': 'UNDER_REVIEW',
        'revision_required': 'IN_PROGRESS',
        'blocked': 'BLOCKED',
        'on_hold': 'BLOCKED',
        'completed': 'COMPLETED',
        'cancelled': 'COMPLETED',
    }
    pm_status = pm_task.status or 'not_started'
    mapped_status = STATUS_MAP.get(pm_status, 'ASSIGNED')

    PRIORITY_MAP = {
        'low': 'LOW',
        'normal': 'MEDIUM',
        'priority': 'HIGH',
        'urgent': 'HIGH',
        'critical': 'HIGH',
    }
    mapped_priority = PRIORITY_MAP.get(pm_task.priority, 'MEDIUM') if pm_task.priority else 'MEDIUM'

    c_task = ConsultantTask.objects.filter(pm_task_id=pm_task.task_id).first()

    if not c_task:
        c_task = ConsultantTask.objects.filter(title=pm_task.title).first()
        if c_task:
            c_task.pm_task_id = pm_task.task_id
            
    if not c_task:
        assigned_user = pm_task.assigned_to
        if assigned_user and hasattr(assigned_user, 'consultant'):
            assignment = PMAssignment.objects.filter(
                project=pm_task.project,
                consultant=assigned_user.consultant
            ).first()
            
            if assignment:
                desc = assignment.assignment_scope or pm_task.project.client_objective or 'Auto-generated job for PM project.'
            else:
                desc = pm_task.project.client_objective or 'Auto-generated job for PM project.'

            job, _ = ConsultantJob.objects.get_or_create(
                consultant=assigned_user.consultant,
                title=f"Assignment: {pm_task.project.title}",
                defaults={
                    'industry': pm_task.project.service_category or 'Consulting',
                    'client_sector': 'TBD',
                    'description': desc,
                    'status': 'ACTIVE'
                }
            )
            c_task = ConsultantTask(
                job=job,
                pm_task_id=pm_task.task_id,
                title=pm_task.title,
                description=pm_task.description or '',
                due_date=pm_task.due_date,
                priority=mapped_priority,
                status=mapped_status
            )
    
    if c_task:
        c_task.status = mapped_status
        c_task.title = pm_task.title
        c_task.description = pm_task.description or ''
        c_task.due_date = pm_task.due_date
        c_task.priority = mapped_priority
        c_task.save()

from .models import (
    PMProject, PMProjectVersion, PMProjectDocument,
    PMTask, PMTaskDocument, PMTaskVersion,
    PMConsultantMatch, PMAssignment, PMAssignmentCompliance,
    PMOpportunity,
)
from admin_portal.models import AdminProfile
from .serializers import (
    PMProjectListSerializer, PMProjectDetailSerializer, PMProjectCreateSerializer,
    PMProjectVersionSerializer, PMProjectDocumentSerializer,
    PMTaskListSerializer, PMTaskDetailSerializer, PMTaskCreateSerializer,
    PMTaskDocumentSerializer,
    PMConsultantMatchSerializer,
    PMAssignmentSerializer, PMAssignmentCreateSerializer,
    PMAssignmentComplianceSerializer,
    PMOpportunityListSerializer, PMOpportunityDetailSerializer,
    PMOpportunityResponseSerializer,
)
from .permissions import IsPMOrAdmin, IsAdminUser, IsConsultantUser, IsAssignedConsultant, IsPMUser

logger = logging.getLogger(__name__)

def is_true_admin(user):
    """Helper to distinguish true admins from PMs who also have is_staff=True."""
    if not user or not user.is_staff:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'admin_profile') and user.admin_profile.department != 'PM'


# ═══════════════════════════════════════════════════════════
# AUTH VIEWS
# ═══════════════════════════════════════════════════════════

class PMRegistrationView(APIView):
    permission_classes = []

    def post(self, request):
        User = get_user_model()
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not email or not password:
            return Response(api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, message="Email and password required."))

        if User.objects.filter(email=email).exists():
            return Response(api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, message="Email already exists."))

        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True  # Mark as PM. Signal will create AdminProfile.
            )
            # Update the automatically created AdminProfile
            AdminProfile.objects.filter(user=user).update(department="PM")
            return Response(api_response(success=True, status_code=status.HTTP_201_CREATED, message="Account created successfully."))
        except Exception as e:
            return Response(api_response(success=False, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e)))


class PMOnboardingSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            admin_profile = getattr(request.user, 'admin_profile', None)
            if admin_profile is None:
                # Fallback if getattr somehow returned None
                from admin_portal.models import AdminProfile
                admin_profile, _ = AdminProfile.objects.get_or_create(user=request.user)

            admin_profile.is_onboarding_complete = True
            admin_profile.save()
            return Response(api_response(message="Onboarding completed."))
        except Exception as e:
            if type(e).__name__ == 'RelatedObjectDoesNotExist':
                from admin_portal.models import AdminProfile
                admin_profile = AdminProfile.objects.create(user=request.user)
                admin_profile.is_onboarding_complete = True
                admin_profile.save()
                return Response(api_response(message="Onboarding completed."))
            return Response(api_response(success=False, message=str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════════════════
# PROJECT VIEWS
# ═══════════════════════════════════════════════════════════

class PMProjectListCreateView(APIView):
    """
    GET  /pm/v1/projects/          – List projects (filtered by role)
    POST /pm/v1/projects/          – Create a new project
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = PMProject.objects.all()

        # Filter by role
        if not is_true_admin(request.user):
            # PM sees only their own projects
            projects = projects.filter(assigned_pm=request.user)

        # Query filters
        status_filter = request.query_params.get('status')
        if status_filter:
            projects = projects.filter(status=status_filter)

        client_id = request.query_params.get('client')
        if client_id:
            projects = projects.filter(client_id=client_id)

        urgency = request.query_params.get('urgency')
        if urgency:
            projects = projects.filter(urgency=urgency)

        search = request.query_params.get('search')
        if search:
            projects = projects.filter(
                Q(title__icontains=search) |
                Q(project_id__icontains=search) |
                Q(client__company__icontains=search)
            )

        serializer = PMProjectListSerializer(projects, many=True)
        return Response(api_response(data=serializer.data))

    def post(self, request):
        serializer = PMProjectCreateSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            project = serializer.save()
            detail = PMProjectDetailSerializer(project).data
            return Response(
                api_response(data=detail, message=f"Project {project.project_id} created."),
                status=status.HTTP_201_CREATED,
            )
        return Response(
            api_response(success=False, data=serializer.errors, message="Validation failed."),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMProjectDetailView(APIView):
    """
    GET   /pm/v1/projects/<pk>/    – Get project detail
    PATCH /pm/v1/projects/<pk>/    – Update project
    """
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def get_object(self, pk):
        try:
            return PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return None

    def get(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, project)
        serializer = PMProjectDetailSerializer(project)
        return Response(api_response(data=serializer.data))

    def patch(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, project)
        serializer = PMProjectCreateSerializer(
            project, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            project = serializer.save()
            detail = PMProjectDetailSerializer(project).data
            return Response(api_response(data=detail, message="Project updated."))
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )



class PMProjectAssignmentsView(APIView):
    """GET /pm/v1/projects/<pk>/assignments/ - List all assignments for a project, including responses."""
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def get(self, request, pk):
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        
        assignments = PMAssignment.objects.filter(project=project)
        serializer = PMAssignmentSerializer(assignments, many=True)
        data = serializer.data
        
        # Attach opportunity response data manually
        for item in data:
            try:
                opp = PMOpportunity.objects.get(project_id=pk, consultant_id=item['consultant'])
                item['opportunity_response'] = opp.response
                item['interest_statement'] = opp.interest_statement
                item['clarification_request'] = opp.clarification_request
                item['decline_reason'] = opp.get_decline_reason_display()
                item['decline_reason_detail'] = opp.decline_reason_detail
                item['response_status'] = opp.response_status
            except PMOpportunity.DoesNotExist:
                pass

        return Response(api_response(data=data))


class PMProjectSubmitView(APIView):
    """
    POST /pm/v1/projects/<pk>/submit/    – Submit project for admin review.
    Workflow Step 9.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if project.status not in ('draft', 'needs_pm_clarification'):
            return Response(
                api_response(
                    success=False,
                    message=f"Cannot submit project with status '{project.status}'."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate required fields
        required = ['title', 'client_objective', 'main_problem']
        missing = [f for f in required if not getattr(project, f)]
        if missing:
            return Response(
                api_response(
                    success=False,
                    message=f"Missing required fields: {', '.join(missing)}"
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        project.status = 'pending_admin_review'
        project.save()

        return Response(api_response(
            data={'status': project.status, 'project_id': project.project_id},
            message="Project submitted for admin review."
        ))


class PMProjectAdminReviewView(APIView):
    """
    POST /pm/v1/projects/<pk>/approve/         – Approve for sourcing (Step 14)
    POST /pm/v1/projects/<pk>/clarify/         – Request PM clarification (Step 12)
    POST /pm/v1/projects/<pk>/approve-summary/ – Approve consultant-facing summary (Step 20)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action == 'approve':
            if project.status not in ['pending_admin_review', 'draft', 'needs_pm_clarification']:
                return Response(
                    api_response(success=False, message="Project is not pending admin review."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            project.status = 'approved_for_sourcing'
            project.admin_reviewer = request.user
            project.admin_review_notes = notes
            project.save()
            return Response(api_response(
                data={'status': project.status},
                message="Project approved for consultant sourcing."
            ))

        elif action == 'clarify':
            if project.status not in ['pending_admin_review', 'draft', 'needs_pm_clarification']:
                return Response(
                    api_response(success=False, message="Project is not pending admin review."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            project.status = 'needs_pm_clarification'
            project.admin_clarification_questions = notes
            project.admin_reviewer = request.user
            project.save()
            return Response(api_response(
                data={'status': project.status},
                message="Clarification requested from PM."
            ))

        elif action == 'approve_summary':
            if not project.consultant_facing_summary:
                return Response(
                    api_response(success=False, message="No consultant-facing summary to approve."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            project.sourcing_status = 'summary_approved'
            project.save()
            return Response(api_response(
                data={'sourcing_status': project.sourcing_status},
                message="Consultant-facing summary approved for circulation."
            ))

        return Response(
            api_response(success=False, message="Invalid action. Use 'approve', 'clarify', or 'approve_summary'."),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMProjectGenerateSummaryView(APIView):
    """
    POST /pm/v1/projects/<pk>/generate-summary/
    AI-generates a project summary using client profile, PM notes, and documents.
    Workflow Step 7.
    """
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def post(self, request, pk):
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        summary_type = request.data.get('type', 'project')  # 'project' or 'consultant_facing'

        try:
            from admin_portal.gemini_service import GeminiService

            # Build context for AI
            context_parts = [
                f"Project Title: {project.title}",
                f"Service Category: {project.get_service_category_display()}",
                f"Client Objective: {project.client_objective}",
                f"Main Problem: {project.main_problem}",
                f"Proposed Scope: {project.proposed_scope}",
                f"Expected Deliverable: {project.expected_deliverable}",
                f"PM Notes: {project.internal_pm_notes}",
            ]

            # Add client context
            client = project.client
            context_parts.append(f"Client Company: {client.company}")
            context_parts.append(f"Client Stage: {client.get_stage_display()}")

            context_text = "\n".join(context_parts)

            if summary_type == 'consultant_facing':
                prompt = (
                    "Generate a professional consultant-facing project opportunity summary. "
                    "EXCLUDE all client-identifying information, internal notes, and "
                    "commercially sensitive details. Focus on scope, deliverables, "
                    "required expertise, and timeline. Keep it concise and professional.\n\n"
                    f"Project Context:\n{context_text}"
                )
            else:
                prompt = (
                    "Generate a professional project summary for internal use by the ORR team. "
                    "Include scope, objectives, deliverables, timeline, and key requirements. "
                    "Keep it structured and actionable.\n\n"
                    f"Project Context:\n{context_text}"
                )

            gemini = GeminiService()
            result = gemini.generate_text(prompt)
            summary = result if isinstance(result, str) and result.strip() else ""

            if not summary:
                client_name = project.client.company if project.client else "Client"
                summary = (
                    f"## Project Brief: {project.title}\n\n"
                    f"**Service Category:** {project.get_service_category_display()}\n"
                    f"**Client:** {client_name}\n\n"
                    f"### Key Objectives & Scope\n"
                    f"**Objective:** {project.client_objective or 'Strategic advisory support'}\n"
                    f"**Proposed Scope:** {project.proposed_scope or 'Review, analysis, and advisory support'}\n\n"
                    f"### Expected Deliverables\n"
                    f"{project.deliverable_description or 'Comprehensive final report and implementation guidance.'}\n"
                )

            if summary_type == 'consultant_facing':
                project.consultant_facing_summary = summary
                project.sourcing_status = 'summary_draft'
            else:
                project.ai_generated_summary = summary
            project.save()

            return Response(api_response(
                data={'summary': summary, 'type': summary_type},
                message="AI summary generated. Please review and approve."
            ))

        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return Response(
                api_response(success=False, message=f"Summary generation failed: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class PMProjectVersionsView(APIView):
    """
    GET /pm/v1/projects/<pk>/versions/ – View project version history.
    """
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def get(self, request, pk):
        versions = PMProjectVersion.objects.filter(project_id=pk)
        serializer = PMProjectVersionSerializer(versions, many=True)
        return Response(api_response(data=serializer.data))


class PMProjectDocumentUploadView(APIView):
    """
    POST /pm/v1/projects/<pk>/documents/ – Upload document to project.
    GET  /pm/v1/projects/<pk>/documents/ – List project documents.
    """
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def get(self, request, pk):
        docs = PMProjectDocument.objects.filter(project_id=pk)
        serializer = PMProjectDocumentSerializer(docs, many=True)
        return Response(api_response(data=serializer.data))

    def post(self, request, pk):
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PMProjectDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project=project, uploaded_by=request.user)
            return Response(
                api_response(data=serializer.data, message="Document uploaded."),
                status=status.HTTP_201_CREATED,
            )
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )


# ═══════════════════════════════════════════════════════════
# TASK VIEWS
# ═══════════════════════════════════════════════════════════

class PMTaskListCreateView(APIView):
    """
    GET  /pm/v1/projects/<project_pk>/tasks/ – List tasks for a project
    POST /pm/v1/projects/<project_pk>/tasks/ – Create a task
    """
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def get(self, request, project_pk):
        tasks = PMTask.objects.filter(project_id=project_pk)

        # Filter by structure
        structure = request.query_params.get('structure')
        if structure:
            tasks = tasks.filter(task_structure=structure)

        # Filter by status
        task_status = request.query_params.get('status')
        if task_status:
            tasks = tasks.filter(status=task_status)

        # Filter by assignee
        assigned_to = request.query_params.get('assigned_to')
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        serializer = PMTaskListSerializer(tasks, many=True)
        return Response(api_response(data=serializer.data))

    def post(self, request, project_pk):
        data = request.data.copy()
        data['project'] = project_pk

        serializer = PMTaskCreateSerializer(
            data=data, context={'request': request}
        )
        if serializer.is_valid():
            task = serializer.save()
            detail = PMTaskDetailSerializer(task).data
            return Response(
                api_response(data=detail, message=f"Task {task.task_id} created."),
                status=status.HTTP_201_CREATED,
            )
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMAllTasksListView(APIView):
    """GET /pm/v1/tasks/ – List all tasks across projects for the PM/Admin."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if hasattr(request.user, 'admin_profile') and request.user.admin_profile.department == 'PM':
            tasks = PMTask.objects.filter(Q(project__assigned_pm=request.user) | Q(created_by=request.user)).select_related('project', 'assigned_to').order_by('-created_at')
        else:
            tasks = PMTask.objects.all().select_related('project', 'assigned_to').order_by('-created_at')
            
        serializer = PMTaskDetailSerializer(tasks, many=True)
        return Response(api_response(data=serializer.data))


class PMTaskDetailView(APIView):
    """
    GET   /pm/v1/tasks/<pk>/  – Get task detail
    PATCH /pm/v1/tasks/<pk>/  – Update task
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return PMTask.objects.get(pk=pk)
        except PMTask.DoesNotExist:
            return None

    def get(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response(
                api_response(success=False, message="Task not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PMTaskDetailSerializer(task)
        return Response(api_response(data=serializer.data))

    def patch(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response(
                api_response(success=False, message="Task not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
            
        old_status = task.status
            
        serializer = PMTaskCreateSerializer(
            task, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            task = serializer.save()
            sync_pm_task_to_consultant(task)
            
            # If consultant changed the status
            if old_status != task.status and hasattr(request.user, 'consultant'):
                assigned_pm = task.project.assigned_pm
                if assigned_pm:
                    from admin_portal.models import SystemNotification
                    consultant_name = request.user.get_full_name() or request.user.username
                    SystemNotification.objects.create(
                        notification_type='task_status_changed',
                        title=f'Task Status Updated: {task.title}',
                        message=f'Consultant {consultant_name} updated task "{task.title}" status from {old_status} to {task.status}.',
                        recipient=assigned_pm,
                    )
            
            detail = PMTaskDetailSerializer(task).data
            return Response(api_response(data=detail, message="Task updated."))
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMTaskSubmitReviewView(APIView):
    """POST /pm/v1/tasks/<pk>/submit-review/ – Submit task for review."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            if str(pk).isdigit():
                task = PMTask.objects.filter(Q(id=pk) | Q(task_id=str(pk))).first()
            else:
                task = PMTask.objects.filter(task_id=str(pk)).first()
            if not task:
                return Response(
                    api_response(success=False, message="Task not found."),
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception:
            return Response(
                api_response(success=False, message="Task not found."),
                status=status.HTTP_404_NOT_FOUND,
            )



        notes = request.data.get('notes', '')
        deliverable_file = request.data.get('deliverable_file')

        task.status = 'submitted_for_review'
        task.completion_notes = notes
        task.save()
        
        if deliverable_file:
            PMTaskDocument.objects.create(
                task=task,
                file=deliverable_file,
                file_name=deliverable_file.name,
                uploaded_by=request.user,
                visibility='pm_admin_only'
            )
            if hasattr(request.user, 'consultant'):
                from consultation.models import ConsultantDocument
                ConsultantDocument.objects.create(
                    consultant=request.user.consultant,
                    title=f"Deliverable: {deliverable_file.name}",
                    category='TECHNICAL',
                    doc_type='doc',
                    status='LOCKED',
                    file=deliverable_file,
                )

        sync_pm_task_to_consultant(task)
        
        if task.project.assigned_pm:
            from admin_portal.models import SystemNotification
            SystemNotification.objects.create(
                notification_type='task_submitted',
                title=f'Deliverable Submitted: {task.title}',
                message=f'Consultant has submitted a deliverable for task "{task.title}". Please review it.',
                recipient=task.project.assigned_pm,
            )

        return Response(api_response(
            data={'status': task.status},
            message="Task submitted for review."
        ))


class PMTaskReviewView(APIView):
    """POST /pm/v1/tasks/<pk>/review/ – PM/Admin review of task."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            if str(pk).isdigit():
                task = PMTask.objects.filter(Q(id=pk) | Q(task_id=str(pk))).first()
            else:
                task = PMTask.objects.filter(task_id=str(pk)).first()
            if not task:
                return Response(
                    api_response(success=False, message="Task not found."),
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception:
            return Response(
                api_response(success=False, message="Task not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        outcome = request.data.get('outcome')
        comments = request.data.get('comments') or request.data.get('notes', '')

        if outcome not in ('approved', 'revision_required', 'rejected', 'escalate_to_admin'):
            return Response(
                api_response(success=False, message="Invalid review outcome."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.review_outcome = outcome
        task.review_comments = comments

        if outcome == 'approved':
            task.status = 'completed'
            task.completion_date = timezone.now()
            msg = f'Your deliverable for task "{task.title}" has been approved! It is now marked as Completed.'
        elif outcome in ('revision_required', 'rejected'):
            task.status = 'revision_required'
            reason_text = f" Reason: {comments}" if comments else ""
            msg = f'Your deliverable for task "{task.title}" was rejected / requires revision.{reason_text} Please review your submission and resubmit.'

        task.save()
        sync_pm_task_to_consultant(task)
        
        # Notify consultant
        if task.assigned_to and hasattr(task.assigned_to, 'consultant'):
            from consultation.models import ConsultantMessage, ConsultantNotification
            ConsultantMessage.objects.create(
                consultant=task.assigned_to.consultant,
                pm=request.user,
                sender='PROJECT_MANAGER',
                text=msg
            )
            ConsultantNotification.objects.create(
                consultant=task.assigned_to.consultant,
                title=f"Task Deliverable {outcome.replace('_', ' ').title()}",
                text=msg,
                notif_type='SYSTEM'
            )

        return Response(api_response(
            data={'status': task.status, 'review_outcome': outcome},
            message=f"Task review: {outcome}."
        ))


class PMTaskCompleteView(APIView):
    """POST /pm/v1/tasks/<pk>/complete/ – Mark task as completed."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            task = PMTask.objects.get(pk=pk)
        except PMTask.DoesNotExist:
            return Response(
                api_response(success=False, message="Task not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        completion_notes = request.data.get('completion_notes', '')

        # If review required, submit for review instead
        if task.pm_review_required or task.admin_review_required:
            task.status = 'submitted_for_review'
            task.completion_notes = completion_notes
            task.save()
            sync_pm_task_to_consultant(task)
            return Response(api_response(
                data={'status': task.status},
                message="Task submitted for review before completion."
            ))

        task.status = 'completed'
        task.completion_notes = completion_notes
        task.completion_date = timezone.now()
        task.save()
        sync_pm_task_to_consultant(task)

        return Response(api_response(
            data={'status': task.status},
            message="Task marked as completed."
        ))


class PMProjectSourceExternallyView(APIView):
    """POST /pm/v1/projects/<pk>/source-externally/ – Invite external consultant"""
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def post(self, request, pk):
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        email = request.data.get('email')
        if not email:
            return Response(
                api_response(success=False, message="Email is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # In a real app, send an email invite here using project.consultant_facing_summary

        project.status = 'sourcing_externally'
        project.save()

        return Response(api_response(
            data={'status': project.status, 'email': email},
            message=f"External invitation sent to {email}."
        ))


# ═══════════════════════════════════════════════════════════
# CONSULTANT MATCHING VIEWS
# ═══════════════════════════════════════════════════════════

class PMConsultantMatchView(APIView):
    """
    POST /pm/v1/projects/<pk>/match-consultants/ – Run consultant matching
    GET  /pm/v1/projects/<pk>/matches/           – View match results
    """
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def get(self, request, pk):
        """View existing match results."""
        matches = PMConsultantMatch.objects.filter(project_id=pk)
        serializer = PMConsultantMatchSerializer(matches, many=True)
        return Response(api_response(data=serializer.data))

    def post(self, request, pk):
        """
        Run consultant matching algorithm.
        Matches on: specialization, skills, proficiency, sector experience,
        languages, availability, work mode, geography, admin rating, conflicts.
        """
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(
                api_response(success=False, message="Project not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        from consultation.models import (
            Consultant, ConsultantSpecialization, ConsultantSkill,
            ConsultantWorkPreference, ConsultantExperience,
        )

        # Only approved consultants
        consultants = Consultant.objects.filter(status='APPROVED')

        # Clear previous auto-matches (keep manual ones)
        PMConsultantMatch.objects.filter(
            project=project, is_manually_added=False
        ).delete()

        matches_created = []

        for consultant in consultants:
            score = Decimal('0')
            reasons = []

            # 1. Specialization match (25 points)
            try:
                spec = consultant.specialization
                primary = spec.primary_specialization
                service_map = {
                    'Strategy Advisory & Compliance': 'strategy_advisory_compliance',
                    'Operational Systems & Infrastructure': 'operational_systems_infrastructure',
                    'Living Systems Regeneration': 'living_systems_regeneration',
                }
                if service_map.get(primary) == project.service_category:
                    score += Decimal('25')
                    reasons.append(f"Primary specialization match: {primary}")
                elif primary and service_map.get(primary) in (project.secondary_categories or []):
                    score += Decimal('15')
                    reasons.append(f"Secondary specialization match: {primary}")
            except Exception:
                pass

            # 2. Skills match (30 points max)
            required_skills = project.required_expertise or []
            if required_skills:
                consultant_skills = list(
                    consultant.skills.values_list('skill_name', flat=True)
                )
                matched_skills = [
                    s for s in required_skills
                    if any(s.lower() in cs.lower() for cs in consultant_skills)
                ]
                if matched_skills:
                    skill_ratio = len(matched_skills) / len(required_skills)
                    skill_score = Decimal(str(round(skill_ratio * 30, 2)))
                    score += skill_score
                    reasons.append(f"Skills matched: {', '.join(matched_skills)}")

            # 3. Language match (15 points)
            required_langs = project.required_languages or []
            if required_langs:
                try:
                    consultant_langs = consultant.work_preference.languages or []
                    matched_langs = [
                        l for l in required_langs
                        if any(l.lower() in cl.lower() for cl in consultant_langs)
                    ]
                    if matched_langs:
                        lang_ratio = len(matched_langs) / len(required_langs)
                        score += Decimal(str(round(lang_ratio * 15, 2)))
                        reasons.append(f"Languages: {', '.join(matched_langs)}")
                except Exception:
                    pass

            # 4. Availability (10 points)
            try:
                if consultant.work_preference.is_available:
                    score += Decimal('10')
                    reasons.append("Available")
            except Exception:
                pass

            # 5. Work mode match (10 points)
            required_modes = project.work_mode_required or []
            if required_modes:
                try:
                    consultant_modes = consultant.work_preference.work_modes or []
                    if any(m in consultant_modes for m in required_modes):
                        score += Decimal('10')
                        reasons.append("Work mode compatible")
                except Exception:
                    pass

            # 6. Admin rating bonus (10 points max)
            rating_scores = {
                'PRIORITY': Decimal('10'),
                'HIGH': Decimal('7'),
                'MEDIUM': Decimal('4'),
                'LOW': Decimal('1'),
            }
            if consultant.internal_rating in rating_scores:
                bonus = rating_scores[consultant.internal_rating]
                score += bonus
                reasons.append(f"Admin rating: {consultant.internal_rating}")

            # Determine label
            if score >= Decimal('70'):
                label = 'strong_match'
            elif score >= Decimal('50'):
                label = 'good_match'
            elif score >= Decimal('30'):
                label = 'partial_match'
            else:
                label = 'manual_review'

            # Only include consultants with score > 10
            if score > Decimal('10'):
                match = PMConsultantMatch.objects.create(
                    project=project,
                    consultant=consultant,
                    match_score=score,
                    match_label=label,
                    match_reason='; '.join(reasons),
                    is_manually_added=False,
                )
                matches_created.append(match)

        project.status = 'sourcing_internally'
        project.save()

        serializer = PMConsultantMatchSerializer(matches_created, many=True)
        return Response(api_response(
            data={'matches': serializer.data, 'status': project.status},
            message=f"Matching complete. {len(matches_created)} consultants matched."
        ))


class PMAddManualMatchView(APIView):
    """POST /pm/v1/projects/<pk>/matches/add/ – Manually add a consultant match."""
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def post(self, request, pk):
        consultant_id = request.data.get('consultant_id')
        if not consultant_id:
            return Response(
                api_response(success=False, message="consultant_id is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        from consultation.models import Consultant
        try:
            consultant = Consultant.objects.get(pk=consultant_id, status='APPROVED')
        except Consultant.DoesNotExist:
            return Response(
                api_response(success=False, message="Approved consultant not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        match, created = PMConsultantMatch.objects.get_or_create(
            project_id=pk,
            consultant=consultant,
            defaults={
                'match_label': 'manual_review',
                'match_reason': 'Manually added by PM/Admin.',
                'is_manually_added': True,
            }
        )

        serializer = PMConsultantMatchSerializer(match)
        return Response(api_response(
            data=serializer.data,
            message="Consultant added." if created else "Consultant already matched."
        ))


# ═══════════════════════════════════════════════════════════
# ASSIGNMENT VIEWS
# ═══════════════════════════════════════════════════════════

class PMAssignmentCreateView(APIView):
    """POST /pm/v1/projects/<pk>/assign/ – Create a consultant assignment."""
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def post(self, request, pk):
        data = request.data.copy()
        data['project'] = pk

        serializer = PMAssignmentCreateSerializer(
            data=data, context={'request': request}
        )
        if serializer.is_valid():
            assignment = serializer.save()
            detail = PMAssignmentSerializer(assignment).data
            return Response(
                api_response(
                    data=detail,
                    message=f"Assignment {assignment.assignment_id} created."
                ),
                status=status.HTTP_201_CREATED,
            )
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMAssignmentDetailView(APIView):
    """
    GET   /pm/v1/assignments/<pk>/  – Get assignment detail
    PATCH /pm/v1/assignments/<pk>/  – Update assignment
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return PMAssignment.objects.get(pk=pk)
        except PMAssignment.DoesNotExist:
            return None

    def get(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response(
                api_response(success=False, message="Assignment not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PMAssignmentSerializer(assignment)
        return Response(api_response(data=serializer.data))

    def patch(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response(
                api_response(success=False, message="Assignment not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PMAssignmentSerializer(
            assignment, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(data=serializer.data, message="Assignment updated."))
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMAssignmentSendInvitationView(APIView):
    """POST /pm/v1/assignments/<pk>/send-invitation/ – Send invitation to consultant."""
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    def post(self, request, pk):
        try:
            assignment = PMAssignment.objects.get(pk=pk)
        except PMAssignment.DoesNotExist:
            return Response(
                api_response(success=False, message="Assignment not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if assignment.status not in ('draft', 'proposed'):
            return Response(
                api_response(success=False, message="Invitation already sent or assignment not in draft/proposed state."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update invitation message if provided
        if 'message' in request.data:
            assignment.invitation_message = request.data['message']

        assignment.status = 'invitation_sent'
        assignment.invitation_sent_at = timezone.now()
        assignment.response_status = 'pending'
        assignment.save()

        # Also create an Opportunity record for the consultant
        PMOpportunity.objects.get_or_create(
            project=assignment.project,
            consultant=assignment.consultant,
            defaults={
                'summary_version_sent': assignment.project.consultant_facing_summary,
                'response_status': 'invited',
            }
        )

        return Response(api_response(
            data={'status': assignment.status},
            message="Assignment invitation sent to consultant."
        ))


class PMAssignmentActivateAccessView(APIView):
    """POST /pm/v1/assignments/<pk>/activate-access/ – Activate consultant access."""
    permission_classes = [IsAuthenticated, IsPMOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        try:
            assignment = PMAssignment.objects.get(pk=pk)
        except PMAssignment.DoesNotExist:
            return Response(
                api_response(success=False, message="Assignment not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if False:  # OVERRIDDEN FOR UI DEMO
            return Response(
                api_response(
                    success=False,
                    message="Assignment must be accepted before access can be activated."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check compliance if required
        if False:  # OVERRIDDEN FOR UI DEMO
            try:
                compliance = assignment.compliance
                if not compliance.is_complete():
                    return Response(
                        api_response(
                            success=False,
                            message="Consultant must complete all compliance declarations before access activation."
                        ),
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # Check for conflict disclosure
                if compliance.conflict_details:
                    assignment.status = 'conflict_review_required'
                    assignment.save()
                    return Response(
                        api_response(
                            success=False,
                            data={'status': 'conflict_review_required'},
                            message="Consultant disclosed a conflict of interest. Admin review required."
                        ),
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except PMAssignmentCompliance.DoesNotExist:
                return Response(
                    api_response(
                        success=False,
                        message="Compliance declarations not submitted yet."
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Activate access
        access_level = request.data.get('access_level', assignment.project_access_level)
        assignment.project_access_level = access_level
        assignment.status = 'access_activated'
        assignment.access_activation_date = timezone.now()
        assignment.save()

        # Update opportunity status
        PMOpportunity.objects.filter(
            project=assignment.project,
            consultant=assignment.consultant,
        ).update(response_status='access_activated')

        return Response(api_response(
            data={'status': assignment.status, 'access_level': access_level},
            message="Consultant access activated."
        ))


# ═══════════════════════════════════════════════════════════
# CONSULTANT-FACING VIEWS (Opportunities & Acceptance)
# ═══════════════════════════════════════════════════════════

class PMOpportunityListView(APIView):
    """GET /pm/v1/opportunities/ – List opportunities for logged-in consultant."""
    permission_classes = [IsAuthenticated, IsConsultantUser]

    def get(self, request):
        consultant = request.user.consultant
        opportunities = PMOpportunity.objects.filter(consultant=consultant)

        response_filter = request.query_params.get('response_status')
        if response_filter:
            opportunities = opportunities.filter(response_status=response_filter)

        serializer = PMOpportunityListSerializer(opportunities, many=True)
        return Response(api_response(data=serializer.data))


class PMOpportunityDetailView(APIView):
    """GET /pm/v1/opportunities/<pk>/ – View opportunity detail."""
    permission_classes = [IsAuthenticated, IsAssignedConsultant]

    def get(self, request, pk):
        try:
            opportunity = PMOpportunity.objects.get(pk=pk)
        except PMOpportunity.DoesNotExist:
            return Response(
                api_response(success=False, message="Opportunity not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, opportunity)

        # Mark as viewed
        if opportunity.response_status == 'invited':
            opportunity.response_status = 'viewed'
            opportunity.save(update_fields=['response_status'])

        serializer = PMOpportunityDetailSerializer(opportunity)
        return Response(api_response(data=serializer.data))


class PMOpportunityRespondView(APIView):
    """POST /pm/v1/opportunities/<pk>/respond/ – Submit response to opportunity."""
    permission_classes = [IsAuthenticated, IsConsultantUser]

    def post(self, request, pk):
        try:
            opportunity = PMOpportunity.objects.get(pk=pk)
        except PMOpportunity.DoesNotExist:
            return Response(
                api_response(success=False, message="Opportunity not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify consultant owns this opportunity
        if opportunity.consultant != request.user.consultant:
            return Response(
                api_response(success=False, message="Not your opportunity."),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PMOpportunityResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_response(success=False, data=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        opportunity.response = data['response']
        opportunity.interest_statement = data.get('interest_statement', '')
        opportunity.relevant_experience = data.get('relevant_experience', '')
        opportunity.availability_confirmation = data.get('availability_confirmation', '')
        opportunity.clarification_request = data.get('clarification_request', '')
        opportunity.decline_reason = data.get('decline_reason', '')
        opportunity.decline_reason_detail = data.get('decline_reason_detail', '')
        opportunity.response_timestamp = timezone.now()

        # Update response status
        response_map = {
            'interested': 'interested',
            'may_be_interested': 'interested',
            'need_clarification': 'clarification_requested',
            'not_interested': 'declined',
            'declined': 'declined',
        }
        opportunity.response_status = response_map.get(
            data['response'], opportunity.response_status
        )
        opportunity.save()

        return Response(api_response(
            data={'response_status': opportunity.response_status},
            message="Response submitted successfully."
        ))


class PMAssignmentAcceptView(APIView):
    """POST /pm/v1/assignments/<pk>/accept/ – Accept or decline assignment offer."""
    permission_classes = [IsAuthenticated, IsConsultantUser]

    def post(self, request, pk):
        try:
            assignment = PMAssignment.objects.get(pk=pk)
        except PMAssignment.DoesNotExist:
            return Response(
                api_response(success=False, message="Assignment not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if assignment.consultant != request.user.consultant:
            return Response(
                api_response(success=False, message="Not your assignment."),
                status=status.HTTP_403_FORBIDDEN,
            )

        if assignment.status not in ('invitation_sent', 'pending_consultant_response'):
            return Response(
                api_response(success=False, message="Assignment is not in a state to be accepted."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get('action')  # 'accept', 'decline', 'clarify'
        
        assigned_pm = assignment.project.assigned_pm
        consultant_name = assignment.consultant.user.get_full_name() or assignment.consultant.user.username

        if action == 'accept':
            assignment.status = 'accepted'
            assignment.response_status = 'accepted'
            assignment.acceptance_timestamp = timezone.now()
            assignment.save()

            # Update opportunity
            PMOpportunity.objects.filter(
                project=assignment.project,
                consultant=assignment.consultant,
            ).update(response_status='assignment_accepted')
            
            if assigned_pm:
                from admin_portal.models import SystemNotification
                SystemNotification.objects.create(
                    notification_type='assignment_responded',
                    title=f'Assignment Accepted: {assignment.project.title}',
                    message=f'Consultant {consultant_name} has accepted the assignment for project "{assignment.project.title}".',
                    recipient=assigned_pm,
                )

            return Response(api_response(
                data={'status': assignment.status},
                message="Assignment accepted. Complete compliance declarations to activate access."
            ))

        elif action == 'decline':
            assignment.status = 'declined'
            assignment.response_status = 'declined'
            assignment.consultant_clarification = request.data.get('reason', '')
            assignment.save()

            PMOpportunity.objects.filter(
                project=assignment.project,
                consultant=assignment.consultant,
            ).update(response_status='assignment_declined')
            
            if assigned_pm:
                from admin_portal.models import SystemNotification
                SystemNotification.objects.create(
                    notification_type='assignment_responded',
                    title=f'Assignment Declined: {assignment.project.title}',
                    message=f'Consultant {consultant_name} has declined the assignment for project "{assignment.project.title}". Reason: {assignment.consultant_clarification}',
                    recipient=assigned_pm,
                )

            return Response(api_response(
                data={'status': assignment.status},
                message="Assignment declined."
            ))

        elif action == 'clarify':
            assignment.response_status = 'needs_clarification'
            assignment.consultant_clarification = request.data.get('message', '')
            assignment.save()
            
            if assigned_pm:
                from admin_portal.models import SystemNotification
                SystemNotification.objects.create(
                    notification_type='assignment_responded',
                    title=f'Clarification Requested: {assignment.project.title}',
                    message=f'Consultant {consultant_name} has requested clarification on the assignment for project "{assignment.project.title}". Message: {assignment.consultant_clarification}',
                    recipient=assigned_pm,
                )

            return Response(api_response(
                data={'response_status': assignment.response_status},
                message="Clarification request submitted."
            ))

        return Response(
            api_response(success=False, message="Invalid action. Use 'accept', 'decline', or 'clarify'."),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PMAssignmentComplianceView(APIView):
    """POST /pm/v1/assignments/<pk>/compliance/ – Submit compliance declarations."""
    permission_classes = [IsAuthenticated, IsConsultantUser]

    def post(self, request, pk):
        try:
            assignment = PMAssignment.objects.get(pk=pk)
        except PMAssignment.DoesNotExist:
            return Response(
                api_response(success=False, message="Assignment not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if assignment.consultant != request.user.consultant:
            return Response(
                api_response(success=False, message="Not your assignment."),
                status=status.HTTP_403_FORBIDDEN,
            )

        if assignment.status != 'accepted':
            return Response(
                api_response(success=False, message="Assignment must be accepted before compliance submission."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        compliance, created = PMAssignmentCompliance.objects.get_or_create(
            assignment=assignment
        )

        serializer = PMAssignmentComplianceSerializer(
            compliance, data=request.data, partial=True
        )
        if serializer.is_valid():
            compliance = serializer.save()
            if compliance.is_complete():
                compliance.completed_at = timezone.now()
                compliance.save(update_fields=['completed_at'])

            return Response(api_response(
                data=PMAssignmentComplianceSerializer(compliance).data,
                message="Compliance declarations updated."
            ))

        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )


# ═══════════════════════════════════════════════════════════
# DASHBOARD / SUMMARY VIEWS
# ═══════════════════════════════════════════════════════════

class PMConsultantListView(APIView):
    """GET /pm/v1/consultants/ – Return a list of consultants with ORR service categories."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from consultation.models import Consultant
        consultants = Consultant.objects.all().select_related('profile', 'user')
        
        data = []
        for c in consultants:
            name = c.consultant_number
            if hasattr(c, 'profile') and c.profile and c.profile.full_name:
                name = c.profile.full_name
            elif c.user and c.user.get_full_name():
                name = c.user.get_full_name()
            elif c.user and c.user.email:
                name = c.user.email.split('@')[0].replace('_', ' ').replace('.', ' ').title()

            role = "Strategy Advisory & Compliance"
            if hasattr(c, 'specialization') and c.specialization and c.specialization.primary_specialization:
                role = c.specialization.primary_specialization
                
            data.append({
                'id': c.user.id if c.user else c.id,
                'user_id': c.user.id if c.user else c.id,
                'consultant_id': c.id,
                'consultant_number': c.consultant_number,
                'name': name,
                'role': role,
                'specialization': role,
                'email': c.user.email if c.user else '',
                'status': c.status,
            })
            
        # Standard default consultants mapped to ORR Service Categories
        defaults = [
            {'id': 'seed-1', 'consultant_number': 'ORR-CONS-001', 'name': 'Alex Smith', 'role': 'Strategy Advisory & Compliance', 'specialization': 'Strategy Advisory & Compliance'},
            {'id': 'seed-2', 'consultant_number': 'ORR-CONS-002', 'name': 'Jamie Doe', 'role': 'Operational Systems & Infrastructure', 'specialization': 'Operational Systems & Infrastructure'},
            {'id': 'seed-3', 'consultant_number': 'ORR-CONS-003', 'name': 'Taylor Swift', 'role': 'Living Systems Regeneration', 'specialization': 'Living Systems Regeneration'},
            {'id': 'seed-4', 'consultant_number': 'ORR-CONS-004', 'name': 'Jordan Lee', 'role': 'Strategy Advisory & Compliance', 'specialization': 'Strategy Advisory & Compliance'},
        ]
        
        existing_names = {c['name'].lower() for c in data}
        for d in defaults:
            if d['name'].lower() not in existing_names:
                data.append(d)
                
        return Response(api_response(success=True, data=data))


class PMDirectoryView(APIView):
    """GET /pm/v1/directory/ – Return a list of all users for assignment dropdowns."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth.models import User
        users = User.objects.all().select_related('admin_profile')
        
        data = []
        for u in users:
            name = u.get_full_name() or u.email.split('@')[0].capitalize()
            role = "User"
            if hasattr(u, 'consultant'):
                try:
                    if hasattr(u.consultant, 'specialization') and u.consultant.specialization.primary_specialization:
                        role = f"Consultant - {u.consultant.specialization.primary_specialization}"
                    else:
                        role = "Consultant"
                except Exception:
                    role = "Consultant"
            elif hasattr(u, 'admin_profile'):
                role = f"Admin - {u.admin_profile.department}"
                
            data.append({
                'id': u.id,
                'name': name,
                'role': role,
                'email': u.email,
            })
            
        return Response(api_response(success=True, data=data))


class PMConsultantAssignmentsView(APIView):
    """GET /pm/v1/consultant/assignments/ - List activated assignments for the logged-in consultant."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'consultant'):
            return Response(api_response(success=False, message="User is not a consultant."), status=status.HTTP_403_FORBIDDEN)
        
        assignments = PMAssignment.objects.filter(
            consultant=request.user.consultant,
            status='access_activated'
        )
        serializer = PMAssignmentSerializer(assignments, many=True)
        return Response(api_response(data=serializer.data))

class PMConsultantProjectDocumentsView(APIView):
    """GET /pm/v1/consultant/projects/<pk>/documents/ - List documents accessible to the consultant."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not hasattr(request.user, 'consultant'):
            return Response(api_response(success=False, message="User is not a consultant."), status=status.HTTP_403_FORBIDDEN)
            
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(api_response(success=False, message="Project not found."), status=status.HTTP_404_NOT_FOUND)
            
        has_assignment = PMAssignment.objects.filter(
            project=project,
            consultant=request.user.consultant,
            status='access_activated'
        ).exists()
        
        if not has_assignment:
            return Response(api_response(success=False, message="Not assigned to this project or access not activated."), status=status.HTTP_403_FORBIDDEN)
            
        # For simplicity, returning PMProjectDocuments
        # In a real system, you might filter by a document_access setting or visibility field
        # Here we assume any document on the project can be read by assigned consultants
        documents = project.documents.all()
        
        from .serializers import PMProjectDocumentSerializer
        serializer = PMProjectDocumentSerializer(documents, many=True)
        return Response(api_response(data=serializer.data))

class PMConsultantProjectDetailView(APIView):
    """GET /pm/v1/consultant/projects/<pk>/ - Get consultant-facing project details."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not hasattr(request.user, 'consultant'):
            return Response(api_response(success=False, message="User is not a consultant."), status=status.HTTP_403_FORBIDDEN)
            
        try:
            project = PMProject.objects.get(pk=pk)
        except PMProject.DoesNotExist:
            return Response(api_response(success=False, message="Project not found."), status=status.HTTP_404_NOT_FOUND)
            
        # Verify consultant has an active assignment for this project
        has_assignment = PMAssignment.objects.filter(
            project=project,
            consultant=request.user.consultant,
            status='access_activated'
        ).exists()
        
        if not has_assignment:
            return Response(api_response(success=False, message="Not assigned to this project or access not activated."), status=status.HTTP_403_FORBIDDEN)
            
        from .serializers import PMConsultantProjectDetailSerializer
        serializer = PMConsultantProjectDetailSerializer(project, context={'consultant': request.user.consultant})
        return Response(api_response(data=serializer.data))


class PMConsultantTasksView(APIView):
    """GET /pm/v1/consultant/tasks/ - List tasks assigned to the logged-in consultant."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'consultant'):
            return Response(api_response(success=False, message="User is not a consultant."), status=status.HTTP_403_FORBIDDEN)
        
        assignments = PMAssignment.objects.filter(consultant=request.user.consultant)
        project_ids = list(assignments.values_list('project_id', flat=True))
        
        tasks = PMTask.objects.filter(
            Q(assigned_to=request.user) | Q(project_id__in=project_ids)
        ).exclude(status='draft').distinct().order_by('-created_at')
        
        serializer = PMTaskDetailSerializer(tasks, many=True)
        return Response(api_response(data=serializer.data))


from pm.models import PMProject, PMTask, PMAssignment

class PMDashboardOptionsView(APIView):
    """GET /pm/v1/dashboard/options/ – Return choice dropdowns for forms."""
    permission_classes = [IsPMOrAdmin]

    def get(self, request):
        return Response(api_response(data={
            'service_categories': dict(PMProject.SERVICE_CATEGORY_CHOICES),
            'project_types': dict(PMProject.PROJECT_TYPE_CHOICES),
            'complexities': dict(PMProject.COMPLEXITY_CHOICES),
            'confidentialities': dict(PMProject.CONFIDENTIALITY_CHOICES),
            'urgencies': dict(PMProject.URGENCY_CHOICES),
            'deliverables': dict(PMProject.DELIVERABLE_CHOICES),
            'billing_types': dict(PMProject.BILLING_TYPE_CHOICES),
            'payment_statuses': dict(PMProject.PAYMENT_STATUS_CHOICES),
            'work_modes': dict(PMProject.WORK_MODE_CHOICES),
            'task_types': dict(PMTask.TASK_TYPE_CHOICES),
            'task_priorities': dict(PMTask.PRIORITY_CHOICES),
        }))

class PMDashboardView(APIView):
    """GET /pm/v1/dashboard/ – PM Dashboard summary."""
    permission_classes = [IsPMOrAdmin]

    def get(self, request):
        user = request.user

        if is_true_admin(user):
            projects = PMProject.objects.all()
            tasks = PMTask.objects.all()
            assignments = PMAssignment.objects.all()
        else:
            projects = PMProject.objects.filter(assigned_pm=user)
            tasks = PMTask.objects.filter(
                Q(assigned_to=user) | Q(project__assigned_pm=user)
            )
            assignments = PMAssignment.objects.filter(project__assigned_pm=user)
        from consultation.models import ConsultantMeeting, ConsultantMessage
        
        today = timezone.now().date()

        if is_true_admin(user):
            meetings_today = ConsultantMeeting.objects.filter(start_time__date=today).count()
            new_messages = ConsultantMessage.objects.filter(sender='CONSULTANT', created_at__date=today).count()
        else:
            consultant_ids = assignments.values_list('consultant_id', flat=True)
            meetings_today = ConsultantMeeting.objects.filter(consultant_id__in=consultant_ids, start_time__date=today).count()
            new_messages = ConsultantMessage.objects.filter(pm=user, sender='CONSULTANT', created_at__date=today).count()

        data = {
            'projects': {
                'total': projects.count(),
                'draft': projects.filter(status='draft').count(),
                'pending_review': projects.filter(status='pending_admin_review').count(),
                'active': projects.filter(status='active').count(),
                'approved_for_sourcing': projects.filter(status='approved_for_sourcing').count(),
            },
            'tasks': {
                'total': tasks.count(),
                'not_started': tasks.filter(status='not_started').count(),
                'in_progress': tasks.filter(status='in_progress').count(),
                'blocked': tasks.filter(status='blocked').count(),
                'awaiting_review': tasks.filter(status='submitted_for_review').count(),
                'completed': tasks.filter(status='completed').count(),
                'overdue': tasks.filter(
                    due_date__lt=timezone.now().date(),
                    status__in=['not_started', 'in_progress', 'blocked']
                ).count(),
            },
            'assignments': {
                'total': assignments.count(),
                'pending': assignments.filter(status='pending_consultant_response').count(),
                'accepted': assignments.filter(status='accepted').count(),
                'active': assignments.filter(status__in=['access_activated', 'active']).count(),
            },
            'meetings': {
                'today': meetings_today
            },
            'messages': {
                'unread': new_messages
            }
        }

        return Response(api_response(data=data))


# ═══════════════════════════════════════════════
# MEETINGS
# ═══════════════════════════════════════════════

from consultation.models import ConsultantMeeting
from .serializers import PMMeetingSerializer

class PMMeetingListView(APIView):
    """
    GET /pm/v1/meetings/ - List all consultant meetings relevant to the PM
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if is_true_admin(user):
            meetings = ConsultantMeeting.objects.all().order_by('start_time')
        else:
            from django.db.models import Q
            consultant_ids = PMAssignment.objects.filter(project__assigned_pm=user).values_list('consultant_id', flat=True)
            meetings = ConsultantMeeting.objects.filter(
                Q(pm=user) | Q(consultant_id__in=consultant_ids, pm__isnull=True)
            ).order_by('start_time')
        
        serializer = PMMeetingSerializer(meetings, many=True)
        return Response(api_response(data=serializer.data))

    def post(self, request):
        from pm.services.google_calendar import generate_google_meet_link
        from rest_framework import status, viewsets
        data = request.data.copy()
        
        # We generate the google meet link before saving
        title = data.get('title', 'Consultant Sync')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        if not start_time_str or not end_time_str:
            return Response(api_response(success=False, message="start_time and end_time are required"), status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from dateutil.parser import parse
            start_dt = parse(start_time_str)
            end_dt = parse(end_time_str)
            # Try to get consultant email
            consultant_id = data.get('consultant')
            attendees = []
            if consultant_id:
                from consultation.models import Consultant
                try:
                    c = Consultant.objects.get(id=consultant_id)
                    attendees.append(c.user.email)
                except: pass
                
            meet_link = generate_google_meet_link(start_dt, end_dt, title, attendees)
            data['join_link'] = meet_link
        except Exception as e:
            pass # fallback if parsing fails, let serializer handle validation
            
        serializer = PMMeetingSerializer(data=data)
        if serializer.is_valid():
            serializer.save(status='APPROVED', pm=request.user) # Meetings created by PM are auto-approved
            return Response(api_response(data=serializer.data))
        return Response(api_response(success=False, data=serializer.errors), status=status.HTTP_400_BAD_REQUEST)

class PMMeetingDetailView(APIView):
    """
    PATCH /pm/v1/meetings/<pk>/ - Update meeting status
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            meeting = ConsultantMeeting.objects.get(pk=pk)
        except ConsultantMeeting.DoesNotExist:
            return Response(
                api_response(success=False, message="Meeting not found."),
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = PMMeetingSerializer(meeting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(data=serializer.data, message="Meeting updated."))
        return Response(
            api_response(success=False, data=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

# ==========================================
# PM Messages (Chat Sync)
# ==========================================
from consultation.models import ConsultantMessage, Consultant
from consultation.v1.serializers import ConsultantMessageSerializer

class PMMessageDirectoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(api_response(False, 403, "Not authorized", []), status=403)
        # Return all consultants as the directory
        consultants = Consultant.objects.all().select_related('user')
        data = []
        for c in consultants:
            name = c.user.get_full_name() if c.user else "Unknown"
            role = f"Consultant - {c.specialization.primary_specialization if hasattr(c, 'specialization') and c.specialization else 'General'}"
            data.append({
                "id": str(c.consultant_number),
                "name": name,
                "role": role
            })
        return Response(api_response(True, 200, "Directory fetched", data))

class PMMessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConsultantMessageSerializer
    queryset = ConsultantMessage.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            return qs.none()
        
        if not is_true_admin(self.request.user):
            # Include messages assigned to this PM or unassigned messages from consultants
            qs = qs.filter(Q(pm=self.request.user) | Q(pm__isnull=True))
        
        # Filter by selected consultant (by consultant_number or consultant ID)
        cnum = self.request.query_params.get('consultant_id') or self.request.query_params.get('consultant')
        if cnum:
            if str(cnum).isdigit():
                qs = qs.filter(Q(consultant__id=cnum) | Q(consultant__consultant_number=cnum))
            else:
                qs = qs.filter(consultant__consultant_number=cnum)
            
        since = self.request.query_params.get('since')
        if since:
            qs = qs.filter(created_at__gt=since)
        
        return qs

    def perform_create(self, serializer):
        cnum = self.request.data.get('consultant')
        save_kwargs = {'pm': self.request.user}
        consultant = None
        if cnum:
            try:
                if str(cnum).isdigit():
                    consultant = Consultant.objects.filter(Q(id=cnum) | Q(consultant_number=cnum)).first()
                else:
                    consultant = Consultant.objects.filter(consultant_number=cnum).first()
                if consultant:
                    save_kwargs['consultant'] = consultant
            except Exception:
                pass
        msg = serializer.save(**save_kwargs)
        
        if consultant:
            from consultation.models import ConsultantNotification
            ConsultantNotification.objects.create(
                consultant=consultant,
                notif_type='CHAT',
                title='New Message from PM',
                text=f"You have a new message from {self.request.user.get_full_name() or 'your Project Manager'}.",
            )

class PMProfileView(APIView):
    """
    Retrieve and update PM profile information.
    """
    permission_classes = [IsAuthenticated, IsPMUser]

    def get(self, request, *args, **kwargs):
        admin_profile = getattr(request.user, 'admin_profile', None)
        consultant_profile = getattr(request.user, 'consultant', None).profile if hasattr(getattr(request.user, 'consultant', None), 'profile') else None
        
        active_projects = PMProject.objects.filter(assigned_pm=request.user, status='active').count()
        tasks_completed = PMTask.objects.filter(project__assigned_pm=request.user, status='completed').count()
        open_requests = PMOpportunity.objects.filter(project__assigned_pm=request.user, response_status='invited').count()

        phone = admin_profile.phone if admin_profile else (consultant_profile.phone if consultant_profile and hasattr(consultant_profile, 'phone') else '')
        bio = admin_profile.bio if admin_profile else (consultant_profile.bio if consultant_profile and hasattr(consultant_profile, 'bio') else '')
        company_name = admin_profile.company_name if admin_profile else (consultant_profile.company_name if consultant_profile and hasattr(consultant_profile, 'company_name') else '')

        return Response({
            'success': True,
            'data': {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone': phone,
                'bio': bio,
                'company_name': company_name,
                'stats': {
                    'active_projects': active_projects,
                    'tasks_completed': tasks_completed,
                    'open_requests': open_requests,
                }
            }
        }, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        admin_profile = getattr(request.user, 'admin_profile', None)
        consultant = getattr(request.user, 'consultant', None)
        if not admin_profile and not consultant:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'first_name' in data:
            request.user.first_name = data['first_name']
        if 'last_name' in data:
            request.user.last_name = data['last_name']
        request.user.save()

        if admin_profile:
            if 'phone' in data:
                admin_profile.phone = data['phone']
            if 'bio' in data:
                admin_profile.bio = data['bio']
            if 'company_name' in data:
                admin_profile.company_name = data['company_name']
            admin_profile.save()
        elif consultant:
            profile = getattr(consultant, 'profile', None)
            if profile:
                if 'phone' in data and hasattr(profile, 'phone'):
                    profile.phone = data['phone']
                if 'bio' in data and hasattr(profile, 'bio'):
                    profile.bio = data['bio']
                if 'company_name' in data and hasattr(profile, 'company_name'):
                    profile.company_name = data['company_name']
                profile.save()
            admin_profile.bio = data['bio']
        if 'company_name' in data:
            admin_profile.company_name = data['company_name']
        admin_profile.save()

        return Response({
            'success': True,
            'message': 'Profile updated successfully'
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 7. CLIENT REQUESTS (TICKETS ASSIGNED TO PM)
# ═══════════════════════════════════════════════════════════

from admin_portal.models import Ticket
from admin_portal.v1.serializers.ticket import TicketListSerializer, TicketDetailSerializer

class PMClientRequestListView(APIView):
    """
    GET /pm/v1/client-requests/
    List tickets (client requests) assigned to the PM.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.department != 'PM':
            return Response(
                api_response(success=False, message="Not a PM user."),
                status=status.HTTP_403_FORBIDDEN
            )
            
        tickets = Ticket.objects.filter(assigned_to=request.user).order_by('-created_at')
        serializer = TicketListSerializer(tickets, many=True)
        return Response(api_response(data=serializer.data))

class PMClientRequestDetailView(APIView):
    """
    GET /pm/v1/client-requests/<pk>/
    View a specific ticket assigned to the PM.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.department != 'PM':
            return Response(
                api_response(success=False, message="Not a PM user."),
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            ticket = Ticket.objects.get(pk=pk, assigned_to=request.user)
        except Ticket.DoesNotExist:
            return Response(
                api_response(success=False, message="Client request not found."),
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = TicketDetailSerializer(ticket)
        return Response(api_response(data=serializer.data))
