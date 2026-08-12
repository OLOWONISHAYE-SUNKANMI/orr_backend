import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.conf import settings
from admin_portal.models import TechnicalFeedback
from admin_portal.v1.serializers.feedback import TechnicalFeedbackSerializer
from common.roles import is_admin
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

@extend_schema(tags=["feedback"])
class TechnicalFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=TechnicalFeedbackSerializer, responses=TechnicalFeedbackSerializer)
    def post(self, request):
        serializer = TechnicalFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.save(user=request.user)
            
            # Email routing to technical team
            try:
                technical_email = getattr(settings, 'TECH_SUPPORT_EMAIL', 'support@orr.solutions')
                
                context = {
                    'subject': feedback.subject,
                    'description': feedback.description,
                    'user_email': request.user.email,
                    'user_name': request.user.get_full_name() or request.user.username,
                    'browser_info': feedback.browser_info,
                    'os_info': feedback.os_info,
                    'url_path': feedback.url_path,
                    'attachment_url': feedback.attachment.url if feedback.attachment else 'None'
                }
                
                html_message = render_to_string('orr_emails/technical_feedback_alert.html', context)
                
                send_mail(
                    subject=f"[ORR Tech Feedback] {feedback.subject}",
                    message=f"New feedback from {context['user_email']}\n\n{feedback.description}",
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@orr.solutions'),
                    recipient_list=[technical_email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Failed to send technical feedback email: {e}")
                
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @extend_schema(responses=TechnicalFeedbackSerializer(many=True))
    def get(self, request):
        if is_admin(request.user):
            feedbacks = TechnicalFeedback.objects.all().order_by('-created_at')
        else:
            feedbacks = TechnicalFeedback.objects.filter(user=request.user).order_by('-created_at')
            
        serializer = TechnicalFeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data)

@extend_schema(tags=["feedback"])
class TechnicalFeedbackDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=TechnicalFeedbackSerializer, responses=TechnicalFeedbackSerializer)
    def patch(self, request, pk):
        from django.shortcuts import get_object_or_404
        feedback = get_object_or_404(TechnicalFeedback, pk=pk)
        
        # Only admins should update status
        if not is_admin(request.user):
            return Response({"status": "error", "message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = TechnicalFeedbackSerializer(feedback, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
