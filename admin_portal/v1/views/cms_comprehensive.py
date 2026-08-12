from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from admin_portal.permissions import CanCreateContent

from admin_portal.models_cms import (
    HowWeOperatePageContent, ProcessStep, ServicesPageContent, ServiceStage, ServicePillar,
    ResourcesBlogsPageContent, ContentCard, LegalPolicyPageContent, PolicyItem, ContactPageContent,
    StrategicAdvisoryPageContent, OperationalSystemsPageContent, LivingSystemsPageContent
)
from admin_portal.cms_utils import (
    CMSErrorHandler, CMSFieldValidator, validate_and_clean_cms_data, CMSValidationError
)
from admin_portal.v1.serializers.cms_comprehensive import (
    HowWeOperatePageContentSerializer, ProcessStepSerializer,
    ServicesPageContentSerializer, ServiceStageSerializer, ServicePillarSerializer,
    ResourcesBlogsPageContentSerializer, ContentCardSerializer,
    LegalPolicyPageContentSerializer, PolicyItemSerializer,
    ContactPageContentSerializer, StrategicAdvisoryPageContentSerializer,
    OperationalSystemsPageContentSerializer, LivingSystemsPageContentSerializer
)


class PublicReadContentWriteMixin:
    """CMS pages back public marketing content: reads are public, but writes
    (PUT/POST/PATCH/DELETE) require content-management rights. Replaces the
    former ``authentication_classes = [] / permission_classes = []`` that left
    these endpoints open to anonymous internet writes.
    """

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsAuthenticated(), CanCreateContent()]


@extend_schema(
    tags=["CMS - How We Operate"],
    summary="Get or update How We Operate page content",
    description="Manage How We Operate page content and process steps."
)
@method_decorator(csrf_exempt, name='dispatch')
class HowWeOperatePageView(PublicReadContentWriteMixin, APIView):
    """How We Operate page content management"""

    def get(self, request):
        page, created = HowWeOperatePageContent.objects.get_or_create(is_active=True)
        steps = ProcessStep.objects.filter(is_active=True).order_by('order')
        
        data = {
            'page': HowWeOperatePageContentSerializer(page).data,
            'steps': ProcessStepSerializer(steps, many=True).data
        }
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Request successful',
            'data': data
        })
    
    def put(self, request):
        page, created = HowWeOperatePageContent.objects.get_or_create(is_active=True)
        
        # Update page data
        page_data = request.data.get('page', {})
        for field in ['hero_title', 'meta_title', 'meta_description']:
            if field in page_data:
                setattr(page, field, page_data[field])
        page.save()
        
        # Update steps data
        steps_data = request.data.get('steps', [])
        for step_data in steps_data:
            step_id = step_data.get('id')
            if step_id:
                try:
                    step = ProcessStep.objects.get(id=step_id)
                    for field in ['step_number', 'title', 'subtitle', 'description', 'bullet1', 'bullet2', 'bullet3', 'bullet4', 'bullet5', 'bullet6', 'bullet7', 'bullet8', 'bullet9', 'wordbreak', 'description1', 'description2', 'description3', 'description4', 'image_url', 'button_text', 'button_text2', 'button_text3', 'order']:
                        if field in step_data:
                            setattr(step, field, step_data[field])
                    step.save()
                except ProcessStep.DoesNotExist:
                    continue
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'How We Operate page updated successfully',
            'data': {'updated': True}
        })


@extend_schema(
    tags=["CMS - Services Page New"],
    summary="Get or update Services page content",
    description="Manage Services page content including stages and pillars."
)
@method_decorator(csrf_exempt, name='dispatch')
class ServicesPageContentView(PublicReadContentWriteMixin, APIView):
    """Services page content management"""

    def get(self, request):
        page, created = ServicesPageContent.objects.get_or_create(is_active=True)
        stages = ServiceStage.objects.filter(is_active=True).order_by('order')
        pillars = ServicePillar.objects.filter(is_active=True).order_by('order')
        
        data = {
            'page': ServicesPageContentSerializer(page).data,
            'stages': ServiceStageSerializer(stages, many=True).data,
            'pillars': ServicePillarSerializer(pillars, many=True).data
        }
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Request successful',
            'data': data
        })
    
    def put(self, request):
        page, created = ServicesPageContent.objects.get_or_create(is_active=True)
        
        # Update page data
        page_data = request.data.get('page', {})
        for field in ['hero_title', 'hero_subtitle', 'pillars_title', 'business_gp_title', 'business_gp_subtitle', 'business_gp_description', 'business_gp_button_text', 'business_gp_image', 'meta_title', 'meta_description']:
            if field in page_data:
                setattr(page, field, page_data[field])
        page.save()
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Services page updated successfully',
            'data': {'updated': True}
        })


@extend_schema(
    tags=["CMS - Resources & Blogs New"],
    summary="Get or update Resources & Blogs page content",
    description="Manage Resources & Blogs page content including content cards."
)
@method_decorator(csrf_exempt, name='dispatch')
class ResourcesBlogsPageContentView(PublicReadContentWriteMixin, APIView):
    """Resources & Blogs page content management"""
    
    
    def get(self, request):
        page, created = ResourcesBlogsPageContent.objects.get_or_create(is_active=True)
        cards = ContentCard.objects.filter(is_active=True).order_by('order')
        
        data = {
            'page': ResourcesBlogsPageContentSerializer(page).data,
            'cards': ContentCardSerializer(cards, many=True).data
        }
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Request successful',
            'data': data
        })
    
    def put(self, request):
        page, created = ResourcesBlogsPageContent.objects.get_or_create(is_active=True)
        
        # Update page data
        page_data = request.data.get('page', {})
        for field in ['hero_title', 'hero_description1', 'hero_description2', 'hero_description3', 'hero_button1_text', 'hero_button2_text', 'meta_title', 'meta_description']:
            if field in page_data:
                setattr(page, field, page_data[field])
        page.save()
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Resources & Blogs page updated successfully',
            'data': {'updated': True}
        })


@extend_schema(
    tags=["CMS - Legal & Policy New"],
    summary="Get or update Legal & Policy page content",
    description="Manage Legal & Policy page content including policy items."
)
@method_decorator(csrf_exempt, name='dispatch')
class LegalPolicyPageContentView(PublicReadContentWriteMixin, APIView):
    """Legal & Policy page content management"""
    
    
    def get(self, request):
        page, created = LegalPolicyPageContent.objects.get_or_create(is_active=True)
        items = PolicyItem.objects.filter(is_active=True).order_by('order')
        
        data = {
            'page': LegalPolicyPageContentSerializer(page).data,
            'items': PolicyItemSerializer(items, many=True).data
        }
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Request successful',
            'data': data
        })
    
    def put(self, request):
        page, created = LegalPolicyPageContent.objects.get_or_create(is_active=True)
        
        # Update page data
        page_data = request.data.get('page', {})
        for field in ['hero_title', 'hero_description', 'meta_title', 'meta_description']:
            if field in page_data:
                setattr(page, field, page_data[field])
        page.save()
        
        # Update items data
        items_data = request.data.get('items', [])
        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id:
                try:
                    item = PolicyItem.objects.get(id=item_id)
                    for field in ['number', 'description', 'order']:
                        if field in item_data:
                            setattr(item, field, item_data[field])
                    item.save()
                except PolicyItem.DoesNotExist:
                    continue
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Legal & Policy page updated successfully',
            'data': {'updated': True}
        })


@extend_schema(
    tags=["CMS - Contact Page New"],
    summary="Get or update Contact page content",
    description="Manage Contact page content including form labels and contact information."
)
@method_decorator(csrf_exempt, name='dispatch')
class ContactPageContentView(PublicReadContentWriteMixin, APIView):
    """Contact page content management"""
    
    
    def get(self, request):
        page = ContactPageContent.objects.filter(is_active=True).first()
        if not page:
            page = ContactPageContent.objects.create(is_active=True)
        
        serializer = ContactPageContentSerializer(page)
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Request successful',
            'data': serializer.data
        })
    
    def put(self, request):
        page = ContactPageContent.objects.filter(is_active=True).first()
        if not page:
            page = ContactPageContent.objects.create(is_active=True)
        
        # Update page data
        for field in ['hero_title', 'contact_info_title', 'contact_info_subtitle', 'phone_number', 'email_address', 'address', 'first_name_label', 'last_name_label', 'email_label', 'phone_label', 'subject_label', 'message_label', 'first_name_placeholder', 'last_name_placeholder', 'email_placeholder', 'phone_placeholder', 'message_placeholder', 'subject_option_1', 'subject_option_2', 'subject_option_3', 'subject_option_4', 'submit_button_text', 'meta_title', 'meta_description']:
            if field in request.data:
                setattr(page, field, request.data[field])
        page.save()
        
        return Response({
            'success': True,
            'status': 200,
            'message': 'Contact page updated successfully',
            'data': {'updated': True}
        })


@extend_schema(
    tags=["CMS - Service Stages"],
    summary="Update individual service stage",
    description="Update individual service stage content."
)
@method_decorator(csrf_exempt, name='dispatch')
class ServiceStageDetailView(PublicReadContentWriteMixin, APIView):
    """Individual service stage management"""
    
    
    def put(self, request, pk):
        try:
            stage = ServiceStage.objects.get(id=pk, is_active=True)
            
            # Update stage data
            for field in ['title', 'subtitle', 'description', 'focus_content', 'button_text']:
                if field in request.data:
                    setattr(stage, field, request.data[field])
            stage.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Service stage updated successfully',
                'data': {
                    'id': stage.id,
                    'title': stage.title,
                    'subtitle': stage.subtitle,
                    'description': stage.description,
                    'focus_content': stage.focus_content,
                    'button_text': stage.button_text,
                }
            })
            
        except ServiceStage.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Service stage not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating service stage: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pk):
        try:
            stage = ServiceStage.objects.get(id=pk, is_active=True)
            return Response({
                'success': True,
                'status': 200,
                'message': 'Service stage retrieved successfully',
                'data': {
                    'id': stage.id,
                    'title': stage.title,
                    'subtitle': stage.subtitle,
                    'description': stage.description,
                    'focus_content': stage.focus_content,
                    'button_text': stage.button_text,
                }
            })
        except ServiceStage.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Service stage not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=["CMS - Service Pillars"],
    summary="Update individual service pillar",
    description="Update individual service pillar content."
)
@method_decorator(csrf_exempt, name='dispatch')
class ServicePillarDetailView(PublicReadContentWriteMixin, APIView):
    """Individual service pillar management"""
    
    
    def put(self, request, pk):
        try:
            pillar = ServicePillar.objects.get(id=pk, is_active=True)
            
            # Update pillar data
            for field in ['title', 'description', 'button_text']:
                if field in request.data:
                    setattr(pillar, field, request.data[field])
            pillar.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Service pillar updated successfully',
                'data': {
                    'id': pillar.id,
                    'title': pillar.title,
                    'description': pillar.description,
                    'button_text': pillar.button_text,
                }
            })
            
        except ServicePillar.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Service pillar not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating service pillar: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pk):
        try:
            pillar = ServicePillar.objects.get(id=pk, is_active=True)
            return Response({
                'success': True,
                'status': 200,
                'message': 'Service pillar retrieved successfully',
                'data': {
                    'id': pillar.id,
                    'title': pillar.title,
                    'description': pillar.description,
                    'button_text': pillar.button_text,
                }
            })
        except ServicePillar.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Service pillar not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=["CMS - Process Steps"],
    summary="Update individual process step",
    description="Update individual process step content."
)
@method_decorator(csrf_exempt, name='dispatch')
class ProcessStepDetailView(PublicReadContentWriteMixin, APIView):
    """Individual process step management"""
    
    
    def put(self, request, pk):
        try:
            step = ProcessStep.objects.get(id=pk, is_active=True)
            
            # Update step data
            for field in ['step_number', 'title', 'subtitle', 'description', 'bullet1', 'bullet2', 'bullet3', 'bullet4', 'bullet5', 'bullet6', 'bullet7', 'bullet8', 'bullet9', 'wordbreak', 'description1', 'description2', 'description3', 'description4', 'image_url', 'button_text', 'button_text2', 'button_text3']:
                if field in request.data:
                    setattr(step, field, request.data[field])
            step.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Process step updated successfully',
                'data': {
                    'id': step.id,
                    'step_number': step.step_number,
                    'title': step.title,
                    'subtitle': step.subtitle,
                    'description': step.description,
                    'bullet1': step.bullet1,
                    'bullet2': step.bullet2,
                    'bullet3': step.bullet3,
                    'bullet4': step.bullet4,
                    'bullet5': step.bullet5,
                    'bullet6': step.bullet6,
                    'bullet7': step.bullet7,
                    'bullet8': step.bullet8,
                    'bullet9': step.bullet9,
                    'wordbreak': step.wordbreak,
                    'description1': step.description1,
                    'description2': step.description2,
                    'description3': step.description3,
                    'description4': step.description4,
                    'image_url': step.image_url,
                    'button_text': step.button_text,
                    'button_text2': step.button_text2,
                    'button_text3': step.button_text3,
                }
            })
            
        except ProcessStep.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Process step not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating process step: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["CMS - Content Cards"],
    summary="Update individual content card",
    description="Update individual content card content."
)
@method_decorator(csrf_exempt, name='dispatch')
class ContentCardDetailView(PublicReadContentWriteMixin, APIView):
    """Individual content card management"""
    
    
    def put(self, request, pk):
        try:
            card = ContentCard.objects.get(id=pk, is_active=True)
            
            # Validate and clean the input data
            try:
                validated_data = validate_and_clean_cms_data(request.data, "content_card")
            except CMSValidationError as e:
                return Response({
                    'success': False,
                    'status': 400,
                    'message': f'Validation error: {str(e)}',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the card with validated data
            for field, value in validated_data.items():
                if hasattr(card, field):
                    setattr(card, field, value)
            
            # Save with comprehensive error handling
            def save_operation():
                card.save()
                return {
                    'success': True,
                    'status': 200,
                    'message': 'Content card updated successfully',
                    'data': {
                        'id': card.id,
                        'badge': card.badge,
                        'title': card.title,
                        'content': card.content,
                        'image_url': card.image_url,
                        'button1_text': card.button1_text,
                        'button2_text': card.button2_text,
                    }
                }
            
            return Response(CMSErrorHandler.safe_cms_operation(save_operation))
            
        except ContentCard.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Content card not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            error_response = CMSErrorHandler.handle_database_error(e, "update content card")
            return Response(error_response, status=error_response['status'])


@extend_schema(
    tags=["CMS - Policy Items"],
    summary="Update individual policy item",
    description="Update individual policy item content."
)
@method_decorator(csrf_exempt, name='dispatch')
class PolicyItemDetailView(PublicReadContentWriteMixin, APIView):
    """Individual policy item management"""
    
    
    def put(self, request, pk):
        try:
            item = PolicyItem.objects.get(id=pk, is_active=True)
            
            # Update item data
            for field in ['number', 'description']:
                if field in request.data:
                    setattr(item, field, request.data[field])
            item.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Policy item updated successfully',
                'data': {
                    'id': item.id,
                    'number': item.number,
                    'description': item.description,
                }
            })
            
        except PolicyItem.DoesNotExist:
            return Response({
                'success': False,
                'status': 404,
                'message': 'Policy item not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating policy item: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# NEW SERVICE PILLAR PAGES ENDPOINTS

@extend_schema(
    tags=["CMS - Strategic Advisory Page"],
    summary="Get Strategic Advisory page content",
    description="Retrieve Strategic Advisory & Compliance page content."
)
@method_decorator(csrf_exempt, name='dispatch')
class StrategicAdvisoryPageView(PublicReadContentWriteMixin, APIView):
    """Strategic Advisory page content management"""
    
    
    def get(self, request):
        try:
            page_content = StrategicAdvisoryPageContent.objects.filter(is_active=True).first()
            
            if not page_content:
                # Create default content if none exists
                page_content = StrategicAdvisoryPageContent.objects.create()
            
            serializer = StrategicAdvisoryPageContentSerializer(page_content)
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Strategic Advisory page content retrieved successfully',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error retrieving Strategic Advisory page content: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        try:
            page_content = StrategicAdvisoryPageContent.objects.filter(is_active=True).first()
            
            if not page_content:
                page_content = StrategicAdvisoryPageContent.objects.create()
            
            # Update fields
            for field in ['hero_title', 'hero_subtitle', 'hero_description', 'hero_image', 'services_title', 
                         'service_1_title', 'service_1_description', 'service_2_title', 'service_2_description',
                         'service_3_title', 'service_3_description', 'process_title', 'process_subtitle',
                         'process_description', 'process_step_1_title', 'process_step_1_subtitle', 'process_step_1',
                         'process_step_2_title', 'process_step_2', 'process_step_3_title', 'process_step_3',
                         'network_title', 'network_description', 'network_cards', 'digital_title', 'digital_subtitle',
                         'digital_description', 'digital_image_alt', 'digital_who_is_this_for', 'digital_features',
                         'case_challenge', 'case_solution', 'case_result', 'case_image_alt', 'cta_title', 
                         'cta_description', 'cta_button_text', 'meta_title', 'meta_description']:
                if field in request.data:
                    setattr(page_content, field, request.data[field])
            
            page_content.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Strategic Advisory page content updated successfully',
                'data': {'id': page_content.id}
            })
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating Strategic Advisory page content: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["CMS - Operational Systems Page"],
    summary="Get Operational Systems page content",
    description="Retrieve Operational Systems & Infrastructure page content."
)
@method_decorator(csrf_exempt, name='dispatch')
class OperationalSystemsPageView(PublicReadContentWriteMixin, APIView):
    """Operational Systems page content management"""
    
    
    def get(self, request):
        try:
            page_content = OperationalSystemsPageContent.objects.filter(is_active=True).first()
            
            if not page_content:
                page_content = OperationalSystemsPageContent.objects.create()
            
            serializer = OperationalSystemsPageContentSerializer(page_content)
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Operational Systems page content retrieved successfully',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error retrieving Operational Systems page content: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        try:
            page_content = OperationalSystemsPageContent.objects.filter(is_active=True).first()
            
            if not page_content:
                page_content = OperationalSystemsPageContent.objects.create()
            
            # Update fields
            for field in ['hero_title', 'hero_subtitle', 'hero_description', 'hero_image', 'services_title', 
                         'service_1_title', 'service_1_description', 'service_2_title', 'service_2_description',
                         'service_3_title', 'service_3_description', 'process_title', 'process_description',
                         'process_step_1_title', 'process_step_1', 'process_step_2_title', 'process_step_2', 
                         'process_step_3_title', 'process_step_3',
                         'case_challenge', 'case_solution', 'case_result', 'case_image_alt',
                         'cta_title', 'cta_description', 'cta_button_text', 'meta_title', 'meta_description']:
                if field in request.data:
                    setattr(page_content, field, request.data[field])
            
            page_content.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Operational Systems page content updated successfully',
                'data': {'id': page_content.id}
            })
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating Operational Systems page content: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["CMS - Living Systems Page"],
    summary="Get Living Systems page content",
    description="Retrieve Living Systems & Regeneration page content."
)
@method_decorator(csrf_exempt, name='dispatch')
class LivingSystemsPageView(PublicReadContentWriteMixin, APIView):
    """Living Systems page content management"""
    
    
    def get(self, request):
        try:
            page_content = LivingSystemsPageContent.objects.filter(is_active=True).first()
            
            if not page_content:
                page_content = LivingSystemsPageContent.objects.create()
            
            serializer = LivingSystemsPageContentSerializer(page_content)
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Living Systems page content retrieved successfully',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error retrieving Living Systems page content: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        try:
            page_content = LivingSystemsPageContent.objects.filter(is_active=True).first()
            
            if not page_content:
                page_content = LivingSystemsPageContent.objects.create()
            
            # Update fields
            for field in ['hero_title', 'hero_subtitle', 'hero_description', 'hero_image', 'services_title', 
                         'service_1_title', 'service_1_description', 'service_2_title', 'service_2_description',
                         'service_3_title', 'service_3_description', 'process_title', 'process_description',
                         'process_step_1', 'process_step_2', 'process_step_3', 'process_step_4',
                         'case_challenge', 'case_solution', 'case_result', 'case_image_alt',
                         'cta_title', 'cta_description', 'cta_button_text', 'meta_title', 'meta_description']:
                if field in request.data:
                    setattr(page_content, field, request.data[field])
            
            page_content.save()
            
            return Response({
                'success': True,
                'status': 200,
                'message': 'Living Systems page content updated successfully',
                'data': {'id': page_content.id}
            })
        except Exception as e:
            return Response({
                'success': False,
                'status': 500,
                'message': f'Error updating Living Systems page content: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)