import uuid
from django.db import transaction
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from common.response import api_response
from consultation.models import (
    Consultant, ConsultantProfile, ConsultantSpecialization,
    ConsultantSkill, ConsultantITCompetence, ConsultantExperience,
    ConsultantWorkPreference, ConsultantCommercial, ConsultantCompliance
)
from .serializers import (
    ConsultantRegistrationSerializer,
    ConsultantVerificationSerializer,
    ConsultantOnboardingSerializer
)

class ConsultantRegistrationView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = ConsultantRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, data=serializer.errors))
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        # Generate Consultant ID: ORR-CONS-XXXXXX
        consultant_count = Consultant.objects.count() + 1
        consultant_id = f"ORR-CONS-{consultant_count:06d}"

        Consultant.objects.create(
            user=user,
            consultant_number=consultant_id,
            status='ACCOUNT_CREATED'
        )

        from admin_portal.orr_email_service import ORREmailService
        
        # Send welcome email using branded template (04-welcome-email.html)
        try:
            ORREmailService.send_welcome_email(
                recipient_email=email,
                dashboard_url=f"https://consultant.orr.solutions/verify",
                consultant_number=consultant_id
            )
        except Exception as e:
            # We fail silently to avoid crashing the API if SMTP isn't configured,
            # but we log it.
            print(f"Failed to send email to {email}: {e}")

        return Response(api_response(
            message="Account created. Verification email sent.",
            data={'consultant_number': consultant_id}
        ))

class ConsultantVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConsultantVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, data=serializer.errors))

        try:
            consultant = Consultant.objects.get(
                user__email=serializer.validated_data['email'],
                consultant_number=serializer.validated_data['consultant_number']
            )
            
            if consultant.status == 'ACCOUNT_CREATED':
                consultant.status = 'EMAIL_VERIFIED'
                consultant.save()
            
            return Response(api_response(
                message="Email verified successfully.",
                data={'consultant_number': consultant.consultant_number, 'status': consultant.status}
            ))
        except Consultant.DoesNotExist:
            return Response(api_response(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message="Consultant not found or details incorrect."
            ))

class ConsultantOnboardingView(APIView):
    # In a real scenario, this is protected and linked to request.user
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, consultant_id=None):
        serializer = ConsultantOnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, data=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        consultant_id = data['consultantId']

        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
        except Consultant.DoesNotExist:
            return Response(
                api_response(success=False, status_code=status.HTTP_404_NOT_FOUND, message="Consultant not found."),
                status=status.HTTP_404_NOT_FOUND
            )

        # 1. Update Consultant Status
        consultant.status = 'PENDING_REVIEW'
        consultant.save()

        # 2. ConsultantProfile
        ConsultantProfile.objects.update_or_create(
            consultant=consultant,
            defaults={
                'full_name': data.get('fullName', ''),
                'display_name': data.get('displayName', ''),
                'phone': data.get('phone', ''),
                'country': data.get('country', ''),
                'timezone': data.get('timezone', ''),
                'professional_title': data.get('jobTitle', ''),
            }
        )

        # 3. ConsultantSpecialization
        ConsultantSpecialization.objects.update_or_create(
            consultant=consultant,
            defaults={
                'primary_specialization': data.get('industry', ''),
                'secondary_specializations': data.get('secondaryIndustries', []),
            }
        )

        # 4. ConsultantSkill (clear old ones if updating, then recreate)
        consultant.skills.all().delete()
        skills_to_create = []
        for skill_name in data.get('skills', []):
            prof = data.get('skillProficiencies', {}).get(skill_name, '')
            exp = data.get('skillYearsExperience', {}).get(skill_name, '')
            skills_to_create.append(ConsultantSkill(
                consultant=consultant,
                skill_name=skill_name,
                proficiency_level=prof,
                years_of_experience=exp
            ))
        
        for custom in data.get('customSkills', []):
            skills_to_create.append(ConsultantSkill(
                consultant=consultant,
                skill_name=custom['name'],
                is_custom=True,
                custom_status='PENDING'
            ))
        ConsultantSkill.objects.bulk_create(skills_to_create)

        # 5. ConsultantITCompetence
        ConsultantITCompetence.objects.update_or_create(
            consultant=consultant,
            defaults={
                'it_confidence': data.get('itConfidence', ''),
                'ai_familiarity': data.get('aiFamiliarity', ''),
                'digital_tools': data.get('itCapabilities', []),
                'software_experience': data.get('softwareExperience', []),
                'data_handling': data.get('dataHandling', []),
            }
        )

        # 6. ConsultantExperience
        ConsultantExperience.objects.update_or_create(
            consultant=consultant,
            defaults={
                'professional_summary': data.get('professionalSummary', ''),
                'sector_experience': data.get('sectorExperience', []),
                'professional_evidence': data.get('professionalEvidence', ''),
                'portfolio_url': data.get('portfolioUrl', ''),
            }
        )

        # 7. ConsultantWorkPreference
        ConsultantWorkPreference.objects.update_or_create(
            consultant=consultant,
            defaults={
                'is_available': data.get('isAvailable', True),
                'weekly_capacity': data.get('weeklyCapacity', ''),
                'preferred_roles': data.get('preferredRoles', []),
                'work_modes': data.get('workModes', []),
                'geo_coverage': data.get('geoCoverage', ''),
                'languages': data.get('languages', []),
            }
        )

        # 8. ConsultantCommercial
        ConsultantCommercial.objects.update_or_create(
            consultant=consultant,
            defaults={
                'hourly_rate': data.get('hourlyRate', ''),
                'currency': data.get('currency', ''),
                'engagement_types': data.get('engagementTypes', []),
            }
        )

        # 9. ConsultantCompliance
        ConsultantCompliance.objects.update_or_create(
            consultant=consultant,
            defaults={
                'right_to_work': data.get('rightToWork', False),
                'confidentiality': data.get('ndaAccepted', False),
                'conflict_of_interest': data.get('conflictOfInterest', False),
                'conflict_details': data.get('conflictDetails', ''),
                'data_protection': data.get('dataProtection', False),
            }
        )

        # Send onboarding completion email (05-onboarding-completion.html)
        try:
            from admin_portal.orr_email_service import ORREmailService
            ORREmailService.send_onboarding_completion(
                recipient_email=consultant.user.email,
                user_name=data.get('fullName', consultant.user.get_full_name()),
                workspace_url='https://consultant.orr.solutions/dashboard',
            )
        except Exception:
            pass  # Don't crash the API if email fails

        return Response(api_response(
            message="Onboarding profile submitted successfully. Status updated to Pending Review."
        ))

class ConsultantProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, consultant_id):
        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
        except Consultant.DoesNotExist:
            return Response(api_response(
                success=False, status_code=status.HTTP_404_NOT_FOUND, message="Consultant not found."
            ))

        data = {
            'profileStatus': consultant.status,
            'email': consultant.user.email,
        }

        # 1. Profile
        if hasattr(consultant, 'profile'):
            parts = consultant.profile.full_name.split(' ', 1)
            data['firstName'] = parts[0] if parts else ''
            data['lastName'] = parts[1] if len(parts) > 1 else ''
            data['displayName'] = consultant.profile.display_name
            data['phone'] = consultant.profile.phone
            data['country'] = consultant.profile.country
            data['timezone'] = consultant.profile.timezone
            data['jobTitle'] = consultant.profile.professional_title
            data['availability'] = consultant.profile.availability

        # 2. Specialization
        if hasattr(consultant, 'specialization'):
            data['consultantCategory'] = consultant.specialization.primary_specialization
            data['primarySpecialization'] = consultant.specialization.primary_specialization
            data['secondarySpecializations'] = consultant.specialization.secondary_specializations
            data['expertiseTags'] = consultant.specialization.expertise_tags
            data['areasOfSpecialization'] = consultant.specialization.areas_of_specialization
            data['consultingMethodologies'] = consultant.specialization.consulting_methodologies
            
            # Map industryExpertise, falling back to sector_experience from onboarding if empty
            if consultant.specialization.industry_expertise:
                data['industryExpertise'] = consultant.specialization.industry_expertise
            elif hasattr(consultant, 'experience') and consultant.experience.sector_experience:
                data['industryExpertise'] = consultant.experience.sector_experience
            else:
                data['industryExpertise'] = []

        # 3. Skills
        data['skills'] = []
        for skill in consultant.skills.all():
            if not skill.is_custom:
                data['skills'].append({
                    'name': skill.skill_name,
                    'level': skill.proficiency_level or 'Intermediate'
                })

        # 4. IT Competence
        if hasattr(consultant, 'it_competence'):
            data['itConfidence'] = consultant.it_competence.it_confidence
            data['aiFamiliarity'] = consultant.it_competence.ai_familiarity
            data['itCapabilities'] = consultant.it_competence.digital_tools
            data['softwareExperience'] = consultant.it_competence.software_experience
            data['dataHandling'] = consultant.it_competence.data_handling

        # 5. Experience
        if hasattr(consultant, 'experience'):
            data['bio'] = consultant.experience.professional_summary
            data['portfolioUrl'] = consultant.experience.portfolio_url
            data['professionalEvidence'] = consultant.experience.professional_evidence
            
            data['yearsOfExperience'] = consultant.experience.years_of_experience
            data['currentCompany'] = consultant.experience.current_company
            data['previousCompanies'] = consultant.experience.previous_companies
            data['certifications'] = consultant.experience.certifications
            data['licenses'] = consultant.experience.licenses
            data['educationalQualifications'] = consultant.experience.educational_qualifications
            data['professionalMemberships'] = consultant.experience.professional_memberships

        # 6. Work Preference
        if hasattr(consultant, 'work_preference'):
            data['isAvailable'] = consultant.work_preference.is_available
            data['weeklyCapacity'] = consultant.work_preference.weekly_capacity
            data['preferredRoles'] = consultant.work_preference.preferred_roles
            data['workModes'] = consultant.work_preference.work_modes
            data['geoCoverage'] = consultant.work_preference.geo_coverage
            data['languages'] = consultant.work_preference.languages

        # 7. Commercial
        if hasattr(consultant, 'commercials'):
            data['hourlyRate'] = consultant.commercials.hourly_rate
            data['currency'] = consultant.commercials.currency
            data['engagementTypes'] = consultant.commercials.engagement_types

        # 8. Compliance
        if hasattr(consultant, 'compliance'):
            data['rightToWork'] = consultant.compliance.right_to_work
            data['ndaAccepted'] = consultant.compliance.confidentiality
            data['conflictOfInterest'] = consultant.compliance.conflict_of_interest
            data['conflictDetails'] = consultant.compliance.conflict_details
            data['dataProtection'] = consultant.compliance.data_protection

        return Response(api_response(
            message="Profile fetched successfully.",
            data=data
        ))

    def patch(self, request, consultant_id):
        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
        except Consultant.DoesNotExist:
            return Response(api_response(
                success=False, status_code=status.HTTP_404_NOT_FOUND, message="Consultant not found."
            ))
            
        data = request.data
        
        # 1. Update Profile
        if hasattr(consultant, 'profile'):
            profile = consultant.profile
            if 'firstName' in data or 'lastName' in data:
                first = data.get('firstName', profile.full_name.split(' ')[0] if profile.full_name else '')
                last = data.get('lastName', ' '.join(profile.full_name.split(' ')[1:]) if profile.full_name else '')
                profile.full_name = f"{first} {last}".strip()
            if 'displayName' in data:
                profile.display_name = data['displayName']
            if 'phone' in data:
                profile.phone = data['phone']
            if 'country' in data:
                profile.country = data['country']
            if 'timezone' in data:
                profile.timezone = data['timezone']
            if 'jobTitle' in data:
                profile.professional_title = data['jobTitle']
            if 'availability' in data:
                profile.availability = data['availability']
            profile.save()
            
        # 2. Update Specialization
        if hasattr(consultant, 'specialization'):
            spec = consultant.specialization
            if 'consultantCategory' in data:
                spec.primary_specialization = data['consultantCategory']
            if 'secondarySpecializations' in data:
                spec.secondary_specializations = data['secondarySpecializations']
            if 'expertiseTags' in data:
                spec.expertise_tags = data['expertiseTags']
            if 'areasOfSpecialization' in data:
                spec.areas_of_specialization = data['areasOfSpecialization']
            if 'consultingMethodologies' in data:
                spec.consulting_methodologies = data['consultingMethodologies']
            if 'industryExpertise' in data:
                spec.industry_expertise = data['industryExpertise']
            spec.save()
            
        # 3. Update IT Competence (Skills & Expertise)
        if hasattr(consultant, 'it_competence'):
            it_comp = consultant.it_competence
            if 'itConfidence' in data:
                it_comp.it_confidence = data['itConfidence']
            if 'aiFamiliarity' in data:
                it_comp.ai_familiarity = data['aiFamiliarity']
            if 'itCapabilities' in data:
                it_comp.digital_tools = data['itCapabilities']
            if 'softwareExperience' in data:
                it_comp.software_experience = data['softwareExperience']
            if 'dataHandling' in data:
                it_comp.data_handling = data['dataHandling']
            it_comp.save()
            
        # 4. Update Experience
        if hasattr(consultant, 'experience'):
            exp = consultant.experience
            if 'bio' in data:
                exp.professional_summary = data['bio']
            if 'portfolioUrl' in data:
                exp.portfolio_url = data['portfolioUrl']
            if 'professionalEvidence' in data:
                exp.professional_evidence = data['professionalEvidence']
            if 'yearsOfExperience' in data:
                try:
                    exp.years_of_experience = int(data['yearsOfExperience'])
                except (ValueError, TypeError):
                    pass
            if 'currentCompany' in data:
                exp.current_company = data['currentCompany']
            if 'previousCompanies' in data:
                exp.previous_companies = data['previousCompanies']
            if 'certifications' in data:
                exp.certifications = data['certifications']
            if 'licenses' in data:
                exp.licenses = data['licenses']
            if 'educationalQualifications' in data:
                exp.educational_qualifications = data['educationalQualifications']
            if 'professionalMemberships' in data:
                exp.professional_memberships = data['professionalMemberships']
            exp.save()

        # 5. Update Skills
        if 'skills' in data:
            consultant.skills.filter(is_custom=False).delete()
            skills_to_create = []
            for skill_obj in data['skills']:
                if isinstance(skill_obj, dict):
                    name = skill_obj.get('name')
                    level = skill_obj.get('level', 'Intermediate')
                else:
                    name = skill_obj
                    level = 'Intermediate'
                if name:
                    skills_to_create.append(ConsultantSkill(
                        consultant=consultant,
                        skill_name=name,
                        proficiency_level=level
                    ))
            ConsultantSkill.objects.bulk_create(skills_to_create)

        # 6. Update Work Preference
        if hasattr(consultant, 'work_preference'):
            wp = consultant.work_preference
            if 'languages' in data:
                wp.languages = data['languages']
            wp.save()

        # 7. User Email (Personal)
        if 'email' in data:
            consultant.user.email = data['email']
            consultant.user.save()
            
        return Response(api_response(message="Profile updated successfully.", data=data))



from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ConsultantJobSerializer, ConsultantTaskSerializer
from consultation.models import ConsultantJob, ConsultantTask
from django.utils import timezone





class ConsultantJobViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantJobSerializer
    # In a real app, use IsAuthenticated and filter by request.user.consultant
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Allow passing consultant_id via query params for testing if needed
        consultant_id = self.request.query_params.get('consultantId')
        if consultant_id:
            return ConsultantJob.objects.filter(consultant__consultant_number=consultant_id)
        return ConsultantJob.objects.all()

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        job = self.get_object()
        if job.status == 'OFFERED':
            job.status = 'ACTIVE'
            job.accepted_at = timezone.now()
            job.save()
            
            # Automatically create tasks for each deliverable in the job offer (matching frontend mock)
            for idx, deliv in enumerate(job.deliverables):
                ConsultantTask.objects.create(
                    job=job,
                    title=f"Submit: {deliv}",
                    description=f"Deliverable requirement: Complete comprehensive partner verification matching scope: {job.scope[idx] if idx < len(job.scope) else deliv}",
                    priority='HIGH' if idx == 0 else 'MEDIUM',
                    status='ASSIGNED'
                )
            
            return Response({'status': 'job accepted'})
        return Response({'status': 'job cannot be accepted'}, status=400)

class ConsultantTaskViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantTaskSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        job_id = self.request.query_params.get('jobId')
        if job_id:
            return ConsultantTask.objects.filter(job_id=job_id)
        return ConsultantTask.objects.all()

from .serializers import ConsultantInvoiceSerializer, ConsultantDocumentSerializer, ConsultantMessageSerializer, ConsultantMeetingSerializer, ConsultantNotificationSerializer
from consultation.models import ConsultantInvoice, ConsultantDocument, ConsultantMessage, ConsultantMeeting, ConsultantNotification

class ConsultantInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantInvoiceSerializer
    permission_classes = [AllowAny]
    queryset = ConsultantInvoice.objects.all()
    filterset_fields = ['consultant__consultant_number', 'status']

    def perform_create(self, serializer):
        invoice = serializer.save()
        
        # Trigger Templates 25 and 27 on invoice submission
        try:
            from admin_portal.orr_email_service import ORREmailService
            import datetime
            
            # Send confirmation to consultant
            if invoice.consultant and invoice.consultant.user.email:
                ORREmailService.send_consultant_invoice_confirm(
                    recipient_email=invoice.consultant.user.email,
                    consultant_name=invoice.consultant.user.get_full_name() or invoice.consultant.user.username,
                    invoice_id=invoice.invoice_number,
                    amount=f"{invoice.currency} {invoice.amount}",
                    submission_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    invoice_url=f"https://consultant.orr.solutions/invoices/{invoice.id}"
                )
            
            # Notify admins
            from django.contrib.auth.models import User as AdminUser
            admin_emails = list(AdminUser.objects.filter(is_staff=True, is_active=True).values_list('email', flat=True))
            if admin_emails:
                ORREmailService.send_admin_invoice_review(
                    recipient_emails=admin_emails,
                    consultant_name=invoice.consultant.user.get_full_name() if invoice.consultant else "Consultant",
                    invoice_id=invoice.invoice_number,
                    amount=f"{invoice.currency} {invoice.amount}",
                    admin_invoice_url=f"https://admin.orr.solutions/consultant-invoices/{invoice.id}"
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send consultant invoice emails: {e}")

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        invoice = serializer.save()
        new_status = invoice.status
        
        if old_status != new_status and invoice.consultant and invoice.consultant.user.email:
            try:
                from admin_portal.orr_email_service import ORREmailService
                import datetime
                
                # If paid, trigger 28
                if new_status == 'PAID':
                    ORREmailService.send_consultant_payment_sent(
                        recipient_email=invoice.consultant.user.email,
                        consultant_name=invoice.consultant.user.get_full_name() or invoice.consultant.user.username,
                        invoice_id=invoice.invoice_number,
                        amount=f"{invoice.currency} {invoice.amount}",
                        payment_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                        payment_reference="Check Portal",
                        invoice_url=f"https://consultant.orr.solutions/invoices/{invoice.id}"
                    )
                else:
                    # Otherwise trigger 26 for general status update
                    # Assuming status might be 'APPROVED', 'REJECTED', 'PROCESSING'
                    ORREmailService.send_consultant_invoice_status(
                        recipient_email=invoice.consultant.user.email,
                        invoice_id=invoice.invoice_number,
                        new_status=new_status,
                        status_reason="Status has been updated by admin.",
                        invoice_url=f"https://consultant.orr.solutions/invoices/{invoice.id}"
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send consultant invoice status emails: {e}")

class ConsultantDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantDocumentSerializer
    permission_classes = [AllowAny]
    queryset = ConsultantDocument.objects.all()
    filterset_fields = ['consultant__consultant_number', 'job']

class ConsultantMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantMessageSerializer
    permission_classes = [AllowAny]
    queryset = ConsultantMessage.objects.all()
    
    def get_queryset(self):
        qs = super().get_queryset()
        cnum = self.kwargs.get('consultant_id') or self.request.query_params.get('consultant__consultant_number')
        if cnum:
            qs = qs.filter(consultant__consultant_number=cnum)
        pm_id = self.request.query_params.get('pm_id')
        if pm_id:
            if pm_id.isdigit():
                qs = qs.filter(pm_id=pm_id)
            else:
                qs = qs.filter(pm__isnull=True)
        elif self.request.user.is_authenticated and self.request.user.is_staff:
            qs = qs.filter(pm=self.request.user)
            
        since = self.request.query_params.get('since')
        if since:
            qs = qs.filter(created_at__gt=since)
            
        return qs

    def perform_create(self, serializer):
        cnum = self.kwargs.get('consultant_id')
        # Ensure we bind the consultant based on URL parameter if not provided
        save_kwargs = {}
        if cnum:
            from consultation.models import Consultant
            try:
                consultant = Consultant.objects.get(consultant_number=cnum)
                save_kwargs['consultant'] = consultant
            except Consultant.DoesNotExist:
                pass

        if not serializer.validated_data.get('pm') and self.request.user.is_authenticated and self.request.user.is_staff:
            save_kwargs['pm'] = self.request.user

        msg = serializer.save(**save_kwargs)
        
        # If the message is sent by a consultant (sender='CONSULTANT'), notify the PM
        if msg.sender == 'CONSULTANT' and msg.pm and msg.consultant:
            from admin_portal.models import SystemNotification
            consultant_name = msg.consultant.user.get_full_name() or msg.consultant.consultant_number
            SystemNotification.objects.create(
                notification_type='message_received',
                title='New Message from Consultant',
                message=f'Consultant {consultant_name} sent a new message.',
                recipient=msg.pm,
            )

    @action(detail=False, methods=['get'])
    def directory(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # The user requested to only show exactly the 6 PMs.
        # PMs are uniquely identified by their AdminProfile department being "PM"
        staff_users = User.objects.filter(is_staff=True, admin_profile__department="PM").order_by('first_name', 'email')
        
        data = []
        for u in staff_users:
            # We skip users who are actually consultants just in case they have is_staff=True
            if hasattr(u, 'consultant'):
                continue
                
            name = f"{u.first_name} {u.last_name}".strip() or u.email.split('@')[0].capitalize()
            role = 'Project Manager'
                
            data.append({
                'id': str(u.id),
                'name': name,
                'role': role
            })
        return Response(data)

class ConsultantMeetingViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantMeetingSerializer
    permission_classes = [AllowAny]
    queryset = ConsultantMeeting.objects.all()
    filterset_fields = ['consultant__consultant_number']

    def create(self, request, *args, **kwargs):
        from pm.services.google_calendar import generate_google_meet_link
        from consultation.models import Consultant
        from django.contrib.auth.models import User

        data = request.data.copy()
        consultant_id = kwargs.get('consultant_id')
        if consultant_id:
            data['consultant'] = consultant_id

        title = data.get('title', 'Consultant Sync')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        pm_id = data.get('pm')

        try:
            from dateutil.parser import parse
            start_dt = parse(start_time_str)
            end_dt = parse(end_time_str)
            
            attendees = []
            if pm_id:
                try:
                    pm_user = User.objects.get(id=pm_id)
                    attendees.append(pm_user.email)
                except User.DoesNotExist:
                    pass
            
            meet_link = generate_google_meet_link(start_dt, end_dt, title, attendees)
            data['join_link'] = meet_link
        except Exception:
            pass # fallback if parsing fails

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ConsultantNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultantNotificationSerializer
    permission_classes = [AllowAny]
    queryset = ConsultantNotification.objects.all()
    filterset_fields = ['consultant__consultant_number', 'is_read']

class ConsultantDocumentListView(APIView):
    def get(self, request, consultant_id):
        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
        except Consultant.DoesNotExist:
            return Response(api_response(success=False, status_code=status.HTTP_404_NOT_FOUND, message="Consultant not found."))
            
        docs = ConsultantDocument.objects.filter(consultant=consultant).order_by('-created_at')
        serializer = ConsultantDocumentSerializer(docs, many=True)
        return Response(api_response(data=serializer.data))

    def post(self, request, consultant_id):
        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
        except Consultant.DoesNotExist:
            return Response(api_response(success=False, status_code=status.HTTP_404_NOT_FOUND, message="Consultant not found."))
            
        data = request.data.copy()
        data['consultant'] = consultant_id
        
        serializer = ConsultantDocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(message="Document created successfully.", data=serializer.data))
        return Response(api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, message="Invalid document data.", data=serializer.errors))

class ConsultantDocumentDetailView(APIView):
    def patch(self, request, consultant_id, pk):
        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
            doc = ConsultantDocument.objects.get(id=pk, consultant=consultant)
        except (Consultant.DoesNotExist, ConsultantDocument.DoesNotExist):
            return Response(api_response(success=False, status_code=status.HTTP_404_NOT_FOUND, message="Document not found."))
            
        serializer = ConsultantDocumentSerializer(doc, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(message="Document updated successfully.", data=serializer.data))
        return Response(api_response(success=False, status_code=status.HTTP_400_BAD_REQUEST, message="Invalid data.", data=serializer.errors))

    def delete(self, request, consultant_id, pk):
        try:
            consultant = Consultant.objects.get(consultant_number=consultant_id)
            doc = ConsultantDocument.objects.get(id=pk, consultant=consultant)
        except (Consultant.DoesNotExist, ConsultantDocument.DoesNotExist):
            return Response(api_response(success=False, status_code=status.HTTP_404_NOT_FOUND, message="Document not found."))
            
        doc.delete()
        return Response(api_response(message="Document deleted successfully."))


from django.contrib.auth.models import User

class ConsultantMessageDirectoryView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, consultant_id):
        # MVP: return staff users (Project Managers)
        pms = User.objects.filter(
            is_staff=True, 
            is_superuser=False
        ).exclude(
            client_profile__isnull=False
        ).exclude(
            consultant__isnull=False
        )
        data = [{"id": str(pm.id), "name": f"{pm.first_name} {pm.last_name}".strip() or pm.username, "role": "Project Manager"} for pm in pms]
        # Ensure we always have at least one dummy if db is empty, or just return data
        if not data:
            data = [{"id": "admin", "name": "Admin System", "role": "Project Manager"}]
        return Response(api_response(data=data))
