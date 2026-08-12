from django.core.management.base import BaseCommand
from admin_portal.models_cms import (
    HomePage, ServiceCard, FAQ, ContactInfo, SiteSettings,
    ApproachSection, BusinessSystemCard, BusinessSystemSection,
    ORRRoleSection, MessageStrip, ProcessStage, ProcessSection,
    ORRReportSection
)


class Command(BaseCommand):
    help = 'Seed the public CMS singletons (homepage, services, FAQs, sections) with initial content'

    def handle(self, *args, **options):
        # Create Homepage content
        homepage, created = HomePage.objects.get_or_create(
            is_active=True,
            defaults={
                'hero_title': 'ORR Solutions – Listen. Solve. Optimise.',
                'hero_subtitle': 'Your business GP for complex systems — digital and living. We diagnose your bottlenecks, treat your administrative and compliance headaches, and unlock hidden value in your data, your operations, and your projects.',
                'hero_cta_text': 'Book your free initial consultation',
                'hero_cta_link': '/contact',
                'about_title': 'About ORR',
                'about_content': 'We help organizations navigate complex challenges through strategic advisory, digital innovation, and sustainable growth solutions.',
                'services_title': 'Quick Service Snapshot - 3 Pillars',
                'services_subtitle': 'All three pillars are shaped around your context - no generic playbooks',
                'contact_title': 'Get In Touch',
                'contact_subtitle': 'Ready to transform your business?',
                'contact_email': 'info@orr.com',
                'contact_phone': '+1 (555) 123-4567',
                'meta_title': 'ORR Solutions - Business Transformation',
                'meta_description': 'Strategic advisory, digital systems, and living systems solutions for business transformation.'
            }
        )
        
        # Create Service Cards
        services_data = [
            {
                'title': 'Strategic Advisory & Compliance',
                'description': 'Regulatory clarity, ESG and sustainability frameworks, biotechnology and environmental questions - distilled into simple, usable direction for your organisation.',
                'icon': '🎯',
                'pillar': 'strategic',
                'link': '/services/strategic-advisory',
                'order': 1
            },
            {
                'title': 'Digital Systems, Automation & AI',
                'description': 'SOPs, workflows, portals, dashboards, and AI-assisted tools designed around your team\'s habits, constraints and growth plans',
                'icon': '🤖',
                'pillar': 'digital',
                'link': '/services/digital-systems',
                'order': 2
            },
            {
                'title': 'Living Systems & Regeneration',
                'description': 'Support for land, water, species, and ecosystems - tailored to your sites your risks, and your opportunities',
                'icon': '🌱',
                'pillar': 'living',
                'link': '/services/living-systems',
                'order': 3
            }
        ]
        
        for service_data in services_data:
            ServiceCard.objects.get_or_create(
                title=service_data['title'],
                defaults=service_data
            )
        
        # Create FAQs
        faqs_data = [
            {
                'question': 'What does it mean that ORR is a business GP?',
                'answer': 'We work like a general practitioner for your organisation. We listen first, understand your context and constraints, then bring in the right mix of advisory, systems, AI, and nature-related expertise to treat root causes — always anchored in what matters most to you and your customers.',
                'category': 'general',
                'order': 1
            },
            {
                'question': 'What happens in the first meeting?',
                'answer': 'In our first meeting, we focus on understanding your current situation, challenges, and goals. We\'ll discuss your business context, identify key pain points, and explore what success looks like for you. This helps us create a tailored ORR report with actionable recommendations.',
                'category': 'process',
                'order': 2
            },
            {
                'question': 'What is the ORR report?',
                'answer': 'The ORR report is a comprehensive analysis we provide after our first meeting. It outlines key issues affecting your business, proposes quick fixes and long-term improvements, and shows where our advisory, digital systems, or living systems work will have the most impact on your organization.',
                'category': 'services',
                'order': 3
            },
            {
                'question': 'How much do the meetings and report cost?',
                'answer': 'Our meetings are charged at €45/hour on a pro-rata basis, designed to be short, focused, and value-dense. The ORR report fee starts at €220, though the final cost depends on the complexity of your situation and requirements.',
                'category': 'pricing',
                'order': 4
            },
            {
                'question': 'Do I have to keep working with ORR after the report?',
                'answer': 'Not at all. The ORR report is designed to provide value whether you continue working with us or not. It includes actionable recommendations you can implement independently. However, we\'re available to support implementation if you choose to continue our partnership.',
                'category': 'general',
                'order': 5
            }
        ]
        
        for faq_data in faqs_data:
            FAQ.objects.get_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )
        
        # Create Contact Info
        ContactInfo.objects.get_or_create(
            is_active=True,
            defaults={
                'company_name': 'ORR Solutions',
                'email': 'info@orr.com',
                'phone': '+1 (555) 123-4567',
                'address_line1': '123 Business Street',
                'city': 'London',
                'country': 'United Kingdom',
                'linkedin_url': 'https://linkedin.com/company/orr-solutions',
                'twitter_url': 'https://twitter.com/orrsolutions',
                'business_hours': 'Mon-Fri: 9AM-5PM GMT'
            }
        )
        
        # Create Site Settings
        SiteSettings.objects.get_or_create(
            is_active=True,
            defaults={
                'site_name': 'ORR Solutions',
                'site_tagline': 'Listen. Solve. Optimise.',
                'primary_color': '#47ff4c',
                'secondary_color': '#0ec277',
                'accent_color': '#3DFF7C',
                'footer_text': 'Transforming businesses through strategic advisory, digital innovation, and sustainable solutions.',
                'copyright_text': '© 2024 ORR Solutions. All rights reserved.',
                'privacy_policy_url': '/privacy-policy',
                'terms_of_service_url': '/terms-of-service'
            }
        )
        
        # Create Approach Section
        ApproachSection.objects.get_or_create(
            is_active=True,
            defaults={
                'title': 'Supporting Copy',
                'paragraph_1': 'Just like a skilled general practitioner, we start from your story not our framework. We take time to understand how your business really works before prescribing anything.',
                'paragraph_2': 'We\'re not a lone consultant — we\'re a central coordination layer with a distributed network behind it. When needed, we draw on specialists across continents, but you always deal with one point of contact: ORR, focused on what\'s best for you.',
                'paragraph_3': 'We fix what\'s slowing you down, strengthen systems around how your people actually work, and when deeper input is needed, we bring it in at the right moment — always in service of your goals.'
            }
        )
        
        # Create Business System Section
        BusinessSystemSection.objects.get_or_create(
            is_active=True,
            defaults={
                'title': 'Businesses as a Living System',
                'subtitle': 'Think of your organisation like a body'
            }
        )
        
        # Create Business System Cards
        business_cards_data = [
            {'title': 'Organ', 'description': 'Your departments and teams', 'order': 1},
            {'title': 'Nervous System', 'description': 'Your communication channels', 'order': 2},
            {'title': 'Circulatory System', 'description': 'Your cashflow and resources', 'order': 3},
            {'title': 'Immune System', 'description': 'Your risk management and compliance', 'order': 4},
            {'title': 'DNA', 'description': 'Your values, SOPs and Cultures', 'order': 5},
            {'title': 'Metabolism', 'description': 'Your day-to-day operations', 'order': 6},
            {'title': 'Senses', 'description': 'Your awareness and feedback loops', 'order': 7}
        ]
        
        for card_data in business_cards_data:
            BusinessSystemCard.objects.get_or_create(
                title=card_data['title'],
                defaults=card_data
            )
        
        # Create ORR Role Section
        ORRRoleSection.objects.get_or_create(
            is_active=True,
            defaults={
                'title': 'ORR\'s Role',
                'description': 'We act like specialist doctors for your business physiology - but we start from your symptoms and your priorities. We check the health of your system, diagnosis issues, and co-design solutions that your people can actually use, keeping everything working together over time.'
            }
        )
        
        # Create Message Strip
        MessageStrip.objects.get_or_create(
            is_active=True,
            defaults={
                'title': 'Message Strip',
                'message': 'Businesses thrive like living organisms when all their systems work together *around real human needs*. ORR keeps your "business physiology" in peak condition — aligning operations, communication, cash flow, compliance, data, and projects around the people you serve'
            }
        )
        
        # Create Process Section
        ProcessSection.objects.get_or_create(
            is_active=True,
            defaults={
                'title': 'How we work: Five Stages',
                'subtitle': 'Every stage is built around you – your pace, your risk appetite, your resources'
            }
        )
        
        # Create Process Stages
        stages_data = [
            {
                'title': 'Discover - We listen',
                'description': 'You tell us what\'s happening. We map your context, pressures, and goals – and what \'good\' looks like for you.',
                'order': 1
            },
            {
                'title': 'Diagnose - We find root causes',
                'description': 'SOPs, workflows, portals, dashboards, and AI-assisted tools designed around your team\'s habits, constraints and growth plans.',
                'order': 2
            },
            {
                'title': 'Design - We shape solution with you',
                'description': 'We propose clear, actionable structures that fit your reality: advisory, roadmaps, systems, AI helpers, and, where relevant, living systems projects.',
                'order': 3
            },
            {
                'title': 'Deploy - We put them to work together',
                'description': 'We implement with minimal disruption, adapting to how your people work today while preparing them for tomorrow.',
                'order': 4
            },
            {
                'title': 'Grow - We optimise over time',
                'description': 'We monitor, refine, and help you scale intelligently, keeping a feedback loop open with you and your stakeholders.',
                'order': 5
            }
        ]
        
        for stage_data in stages_data:
            ProcessStage.objects.get_or_create(
                title=stage_data['title'],
                defaults=stage_data
            )
        
        # Create ORR Report Section
        ORRReportSection.objects.get_or_create(
            is_active=True,
            defaults={
                'title': 'What you Get: The ORR Report',
                'subtitle': 'After your first meeting, you receive a decision-ready ORR report designed to be immediately useful inside your organisation.',
                'feature_1': 'explain your situation in your language,',
                'feature_2': 'highlights key issues and risks that affect your customers and teams',
                'feature_3': 'proposes quick fixes and longer-term improvements that respect your constraints',
                'feature_4': 'shows where advisory, digital systems/AI, or living-systems work will have most impact'
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated CMS with all homepage content')
        )