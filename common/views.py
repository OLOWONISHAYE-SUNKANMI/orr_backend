from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from common.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema

from admin_portal.models_cms import (
    HomePage, ServiceCard, FAQ, ContactInfo, SiteSettings,
    ApproachSection, BusinessSystemCard, BusinessSystemSection,
    ORRRoleSection, MessageStrip, ProcessStage, ProcessSection,
    ORRReportSection
)
from admin_portal.v1.serializers.cms import (
    HomePageSerializer, ServiceCardSerializer, FAQSerializer, 
    ContactInfoSerializer, SiteSettingsSerializer,
    ApproachSectionSerializer, BusinessSystemCardSerializer,
    BusinessSystemSectionSerializer, ORRRoleSectionSerializer,
    MessageStripSerializer, ProcessStageSerializer,
    ProcessSectionSerializer, ORRReportSectionSerializer
)


@extend_schema(
    tags=["Public CMS"],
    summary="Get homepage content",
    description="Public endpoint for homepage content"
)
class PublicHomepageView(APIView):
    """Public homepage content"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        homepage, _ = HomePage.objects.get_or_create(
            is_active=True,
            defaults={'hero_title': 'Transform Your Business with ORR'}
        )
        services = ServiceCard.objects.filter(is_active=True).order_by('order')
        faqs = FAQ.objects.filter(is_active=True).order_by('category', 'order')
        contact_info, _ = ContactInfo.objects.get_or_create(is_active=True)
        site_settings, _ = SiteSettings.objects.get_or_create(is_active=True)
        
        # New sections
        approach_section, _ = ApproachSection.objects.get_or_create(is_active=True)
        business_system_section, _ = BusinessSystemSection.objects.get_or_create(is_active=True)
        business_system_cards = BusinessSystemCard.objects.filter(is_active=True).order_by('order')
        orr_role_section, _ = ORRRoleSection.objects.get_or_create(is_active=True)
        message_strip, _ = MessageStrip.objects.get_or_create(is_active=True)
        process_section, _ = ProcessSection.objects.get_or_create(is_active=True)
        process_stages = ProcessStage.objects.filter(is_active=True).order_by('order')
        orr_report_section, _ = ORRReportSection.objects.get_or_create(is_active=True)
        
        return Response({
            'homepage': HomePageSerializer(homepage).data,
            'services': ServiceCardSerializer(services, many=True).data,
            'faqs': FAQSerializer(faqs, many=True).data,
            'contact_info': ContactInfoSerializer(contact_info).data,
            'site_settings': SiteSettingsSerializer(site_settings).data,
            'approach_section': ApproachSectionSerializer(approach_section).data,
            'business_system_section': BusinessSystemSectionSerializer(business_system_section).data,
            'business_system_cards': BusinessSystemCardSerializer(business_system_cards, many=True).data,
            'orr_role_section': ORRRoleSectionSerializer(orr_role_section).data,
            'message_strip': MessageStripSerializer(message_strip).data,
            'process_section': ProcessSectionSerializer(process_section).data,
            'process_stages': ProcessStageSerializer(process_stages, many=True).data,
            'orr_report_section': ORRReportSectionSerializer(orr_report_section).data,
        })


class CurrentUserRoleView(APIView):
    """Get current user role information"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'user': request.user.username,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser
        })

import redis
from django.conf import settings

@extend_schema(
    tags=["System"],
    summary="Test Redis connection",
    description="Endpoint to verify if Redis is reachable and working."
)
class RedisTestView(APIView):
    permission_classes = [IsAdminUser]  # admin-only infra diagnostic

    def get(self, request):
        try:
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
            r = redis.from_url(redis_url)
            r.ping()
            return Response({"success": True, "message": "Redis is working properly", "url": redis_url})
        except Exception as e:
            return Response({"success": False, "message": "Redis connection failed", "error": str(e)}, status=500)