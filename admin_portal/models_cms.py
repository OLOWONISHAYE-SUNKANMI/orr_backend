from django.db import models
from django.contrib.auth.models import User
from common.models import Audit
from .fields import RichTextField, PlainRichTextField

from django.utils.text import slugify

class HomePage(Audit):
    """Homepage content management"""
    
    # Hero Section
    hero_title = RichTextField(default={"content": "Transform Your Business with ORR", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "Strategic Advisory, Digital Innovation, and Sustainable Growth Solutions", "format": "html"})
    hero_cta_text = RichTextField(default={"content": "Get Started", "format": "html"})
    hero_cta_link = models.URLField(max_length=500, default="/contact")
    hero_background_image = models.ImageField(upload_to='homepage/', blank=True, null=True)
    
    # About Section
    about_title = RichTextField(default={"content": "About ORR", "format": "html"})
    about_content = RichTextField(default={"content": "We help organizations navigate complex challenges...", "format": "html"})
    about_image = models.ImageField(upload_to='homepage/', blank=True, null=True)
    
    # Services Section
    services_title = RichTextField(default={"content": "Our Services", "format": "html"})
    services_subtitle = RichTextField(default={"content": "", "format": "html"}, blank=True)
    services_glow_image = models.CharField(max_length=500, blank=True, default="/images/services_glow.png")
    
    # Service Cards
    service_1_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_1_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_1_button = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_2_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_2_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_2_button = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_3_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_3_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    service_3_button = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    # Contact Section
    contact_title = RichTextField(default={"content": "Get In Touch", "format": "html"})
    contact_subtitle = RichTextField(default={"content": "", "format": "html"}, blank=True)
    contact_email = models.EmailField(max_length=500, default="info@orr.com")
    contact_phone = models.CharField(max_length=500, blank=True)
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Homepage Content"
        verbose_name_plural = "Homepage Content"
    
    def __str__(self):
        title = self.hero_title.get('content', '') if isinstance(self.hero_title, dict) else str(self.hero_title)
        return f"Homepage - {title}"


class ServiceCard(Audit):
    """Service cards for homepage"""
    
    PILLAR_CHOICES = [
        ('strategic', 'Strategic Advisory & Compliance'),
        ('digital', 'Digital Systems, Automation & AI'),
        ('living', 'Living Systems & Regeneration'),
    ]
    
    title = RichTextField(default={"content": "", "format": "html"})
    description = RichTextField(default={"content": "", "format": "html"})
    icon = models.CharField(max_length=500, help_text="CSS icon class or emoji")
    pillar = models.CharField(max_length=500, choices=PILLAR_CHOICES)
    link = models.URLField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        title_text = self.title.get('content', '') if isinstance(self.title, dict) else str(self.title)
        return title_text


class Testimonial(Audit):
    """Client testimonials"""
    
    client_name = RichTextField(default={"content": "", "format": "html"})
    client_company = RichTextField(default={"content": "", "format": "html"}, blank=True)
    client_role = RichTextField(default={"content": "", "format": "html"}, blank=True)
    testimonial_text = RichTextField(default={"content": "", "format": "html"})
    client_photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    rating = models.PositiveIntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"{self.client_name} - {self.client_company}"


class FAQ(Audit):
    """Frequently Asked Questions"""
    
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('services', 'Services'),
        ('pricing', 'Pricing'),
        ('process', 'Process'),
        ('support', 'Support'),
    ]
    
    question = RichTextField(default={"content": "", "format": "html"})
    answer = RichTextField(default={"content": "", "format": "html"})
    category = models.CharField(max_length=500, choices=CATEGORY_CHOICES, default='general')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['category', 'order', 'question']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        if isinstance(self.question, dict):
            return self.question.get('content', '')
        return str(self.question)


class BlogPost(Audit):
    """Blog posts for homepage"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    title = RichTextField(default={"content": "", "format": "html"})
    slug = models.SlugField(max_length=500, unique=True)
    excerpt = RichTextField(default={"content": "", "format": "html"})
    content = RichTextField(default={"content": "", "format": "html"})
    featured_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=500, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-published_at', '-created_at']
    
    def __str__(self):
        return self.title


class ContactInfo(Audit):
    """Contact information"""
    
    company_name = RichTextField(default={"content": "ORR", "format": "html"})
    address_line1 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    address_line2 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    city = RichTextField(default={"content": "", "format": "html"}, blank=True)
    state = RichTextField(default={"content": "", "format": "html"}, blank=True)
    postal_code = models.CharField(max_length=500, blank=True)
    country = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    phone = models.CharField(max_length=500, blank=True)
    email = models.EmailField(max_length=500)
    website = models.URLField(max_length=500, blank=True)
    
    # Social Media
    linkedin_url = models.URLField(max_length=500, blank=True)
    twitter_url = models.URLField(max_length=500, blank=True)
    facebook_url = models.URLField(max_length=500, blank=True)
    instagram_url = models.URLField(max_length=500, blank=True)
    
    # Business Hours
    business_hours = RichTextField(default={"content": "e.g., Mon-Fri: 9AM-5PM", "format": "html"}, blank=True, help_text="e.g., Mon-Fri: 9AM-5PM")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"
    
    def __str__(self):
        return f"{self.company_name} Contact Info"


class ApproachSection(Audit):
    """Approach section content"""
    
    title = RichTextField(default={"content": "Supporting Copy", "format": "html"})
    paragraph_1 = RichTextField(default={"content": "Just like a skilled general practitioner, we start from your story not our framework. We take time to understand how your business really works before prescribing anything.", "format": "html"})
    paragraph_2 = RichTextField(default={"content": "We're not a lone consultant — we're a central coordination layer with a distributed network behind it. When needed, we draw on specialists across continents, but you always deal with one point of contact: ORR, focused on what's best for you.", "format": "html"})
    paragraph_3 = RichTextField(default={"content": "We fix what's slowing you down, strengthen systems around how your people actually work, and when deeper input is needed, we bring it in at the right moment — always in service of your goals.", "format": "html"})
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Approach Section"
        verbose_name_plural = "Approach Section"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class BusinessSystemCard(Audit):
    """Business as living system cards"""
    
    title = RichTextField(default={"content": "", "format": "html"})
    description = RichTextField(default={"content": "", "format": "html"})
    image = models.ImageField(upload_to='business_systems/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Business System Card"
        verbose_name_plural = "Business System Cards"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class BusinessSystemSection(Audit):
    """Business as living system section"""
    
    title = RichTextField(default={"content": "Businesses as a Living System", "format": "html"})
    subtitle = RichTextField(default={"content": "Think of your organisation like a body", "format": "html"})
    card_1_title = RichTextField(default={"content": "Nervous System", "format": "html"})
    card_1_description = RichTextField(default={"content": "Communication, data flow, and decision-making pathways", "format": "html"})
    card_1_image = models.ImageField(upload_to='business_systems/', blank=True, null=True)
    card_2_title = RichTextField(default={"content": "Circulatory System", "format": "html"})
    card_2_description = RichTextField(default={"content": "Cash flow, resource distribution, and value exchange", "format": "html"})
    card_2_image = models.ImageField(upload_to='business_systems/', blank=True, null=True)
    card_3_title = RichTextField(default={"content": "Immune System", "format": "html"})
    card_3_description = RichTextField(default={"content": "Risk management, compliance, and protective measures", "format": "html"})
    card_3_image = models.ImageField(upload_to='business_systems/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Business System Section"
        verbose_name_plural = "Business System Section"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class ORRRoleSection(Audit):
    """ORR Role section content"""
    
    title = RichTextField(default={"content": "ORR's Role", "format": "html"})
    description = RichTextField(default={"content": "We act like specialist doctors for your business physiology - but we start from your symptoms and your priorities. We check the health of your system, diagnosis issues, and co-design solutions that your people can actually use, keeping everything working together over time.", "format": "html"})
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "ORR Role Section"
        verbose_name_plural = "ORR Role Section"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class MessageStrip(Audit):
    """Message strip/testimonial section"""
    
    title = RichTextField(default={"content": "Message Strip", "format": "html"})
    message = RichTextField(default={"content": "Businesses thrive like living organisms when all their systems work together *around real human needs*. ORR keeps your 'business physiology' in peak condition — aligning operations, communication, cash flow, compliance, data, and projects around the people you serve", "format": "html"})
    user_image_1 = models.CharField(max_length=500, default="")
    user_image_2 = models.CharField(max_length=500, default="")
    user_image_3 = models.CharField(max_length=500, default="")
    user_image_4 = models.CharField(max_length=500, default="")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Message Strip"
        verbose_name_plural = "Message Strip"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class ProcessStage(Audit):
    """Five stages process"""
    
    title = RichTextField(default={"content": "", "format": "html"})
    description = RichTextField(default={"content": "", "format": "html"})
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Process Stage"
        verbose_name_plural = "Process Stages"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class ProcessSection(Audit):
    """Five stages section header"""
    
    title = RichTextField(default={"content": "How we work: Five Stages", "format": "html"})
    subtitle = RichTextField(default={"content": "Every stage is built around you – your pace, your risk appetite, your resources", "format": "html"})
    stage_1_title = RichTextField(default={"content": "Listen", "format": "html"})
    stage_1_description = RichTextField(default={"content": "We start by understanding your current situation", "format": "html"})
    stage_2_title = RichTextField(default={"content": "Diagnose", "format": "html"})
    stage_2_description = RichTextField(default={"content": "Identify key issues and opportunities", "format": "html"})
    stage_3_title = RichTextField(default={"content": "Design", "format": "html"})
    stage_3_description = RichTextField(default={"content": "Co-create solutions that fit your context", "format": "html"})
    stage_4_title = RichTextField(default={"content": "Implement", "format": "html"})
    stage_4_description = RichTextField(default={"content": "Execute changes with your team", "format": "html"})
    stage_5_title = RichTextField(default={"content": "Sustain", "format": "html"})
    stage_5_description = RichTextField(default={"content": "Ensure lasting impact and continuous improvement", "format": "html"})
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Process Section"
        verbose_name_plural = "Process Section"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class ORRReportSection(Audit):
    """ORR Report section content"""
    
    title = RichTextField(default={"content": "What you Get: The ORR Report", "format": "html"})
    subtitle = RichTextField(default={"content": "After your first meeting, you receive a decision-ready ORR report designed to be immediately useful inside your organisation.", "format": "html"})
    feature_1 = RichTextField(default={"content": "explain your situation in your language,", "format": "html"})
    feature_1_image = models.CharField(max_length=500, default="/images/report_feature_1.png")
    feature_2 = RichTextField(default={"content": "highlights key issues and risks that affect your customers and teams", "format": "html"})
    feature_2_image = models.CharField(max_length=500, default="/images/report_feature_2.png")
    feature_3 = RichTextField(default={"content": "proposes quick fixes and longer-term improvements that respect your constraints", "format": "html"})
    feature_3_image = models.CharField(max_length=500, default="/images/report_feature_3.png")
    feature_4 = RichTextField(default={"content": "shows where advisory, digital systems/AI, or living-systems work will have most impact", "format": "html"})
    feature_4_image = models.CharField(max_length=500, default="/images/report_feature_4.png")
    main_image = models.CharField(max_length=500, default="/images/orr_report_main.png")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "ORR Report Section"
        verbose_name_plural = "ORR Report Section"
    
    def __str__(self):
        if isinstance(self.title, dict):
            return self.title.get('content', '')
        return str(self.title)


class ServicesPage(Audit):
    """Services page content management"""
    
    # Hero Section
    hero_title = RichTextField(default={"content": "ORR Solutions - Listen. Solve. Optimise.", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "We treat your organisation as a whole system — digital, regulatory, and living. We listen first, then design the right mix of advisory, systems, AI, and on-the-ground projects so you can move better and grow smarter too.", "format": "html"})
    
    # Process Stages
    stage_1_title = RichTextField(default={"content": "STAGE 1 - DISCOVER", "format": "html"})
    stage_1_subtitle = RichTextField(default={"content": "Listen.", "format": "html"})
    stage_1_description = RichTextField(default={"content": "We start simple: one calm conversation and a quick scan of your reality.", "format": "html"})
    stage_1_focus = RichTextField(default={"content": "We focus on:\n• Your context, people, and pressures\n• Regulatory, operational, data, and environmental risks\n• Which questions actually matter", "format": "html"})
    stage_1_button_text = RichTextField(default={"content": "Sign up", "format": "html"})
    
    stage_2_title = RichTextField(default={"content": "STAGE 2 - DIAGNOSE", "format": "html"})
    stage_2_subtitle = RichTextField(default={"content": "Think. Then listen again.", "format": "html"})
    stage_2_description = RichTextField(default={"content": "We turn symptoms into a clear map of problems and opportunities across three pillars.", "format": "html"})
    stage_2_focus = RichTextField(default={"content": "What happens here:\n• Bottleneck and process mapping\n• Compliance, governance, and risk review\n• Data and living systems scan\n• Prioritised list: urgent, high leverage, later", "format": "html"})
    stage_2_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    stage_3_title = RichTextField(default={"content": "STAGE 3 - DESIGN", "format": "html"})
    stage_3_subtitle = RichTextField(default={"content": "Design.", "format": "html"})
    stage_3_description = RichTextField(default={"content": "We design practical structures not theory decks.", "format": "html"})
    stage_3_focus = RichTextField(default={"content": "Typical Outputs:\n• SOPs and standardised workflows\n• Communication and decision pathways\n• Tech stacks, integration and AI use-case\n• Simple concepts for field or nurture projects\n• Clean, structured data ready for reporting", "format": "html"})
    stage_3_button_1_text = RichTextField(default={"content": "Sign up", "format": "html"})
    stage_3_button_2_text = RichTextField(default={"content": "Learn More on living systems & augmentation", "format": "html"})
    
    stage_4_title = RichTextField(default={"content": "STAGE 4 - DEPLOY", "format": "html"})
    stage_4_subtitle = RichTextField(default={"content": "Solve in practice.", "format": "html"})
    stage_4_description = RichTextField(default={"content": "Design becomes reality with guided implementation.", "format": "html"})
    stage_4_focus = RichTextField(default={"content": "Deployment can include:\n• Admin and records setup\n• Client logging, pipeline, and follow-up flows\n• KPI fit dashboards with AI summaries\n• Staff training in the tools you already use\n• Connecting with external providers where needed", "format": "html"})
    stage_4_button_text = RichTextField(default={"content": "Contact Us", "format": "html"})
    
    stage_5_title = RichTextField(default={"content": "STAGE 5 - GROW", "format": "html"})
    stage_5_subtitle = RichTextField(default={"content": "Optimise.", "format": "html"})
    stage_5_description = RichTextField(default={"content": "Once systems are live, we keep them learning.", "format": "html"})
    stage_5_focus = RichTextField(default={"content": "How we support growth:\n• Ongoing data capture and light analytics\n• Quarterly reviews and system tuning\n• AI-assisted monitoring and early warnings\n• Scenario and 'what if' thinking\n• Light, regular check-ins — your systems clinic", "format": "html"})
    stage_5_button_text = RichTextField(default={"content": "Sign up", "format": "html"})
    
    # Three Pillars Section
    pillars_title = RichTextField(default={"content": "The Three Pillars", "format": "html"})
    
    pillar_1_title = RichTextField(default={"content": "Digital Systems, Automation & AI", "format": "html"})
    pillar_1_description = RichTextField(default={"content": "SOPs, workflows, portals, dashboards, and AI helpers that make work flow with less effort and fewer surprises.", "format": "html"})
    pillar_1_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    pillar_2_title = RichTextField(default={"content": "Strategic Advisory & Compliance", "format": "html"})
    pillar_2_description = RichTextField(default={"content": "Short, sharp clarity on rules, risk, and direction — from regulation and ESG to biotech and environmental questions.", "format": "html"})
    pillar_2_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    pillar_3_title = RichTextField(default={"content": "Living Systems & Regeneration", "format": "html"})
    pillar_3_description = RichTextField(default={"content": "Support for land, water, species, and ecosystems — from production systems to restoration and incident response.", "format": "html"})
    pillar_3_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    # Business GP Section
    business_gp_title = RichTextField(default={"content": "ORR is your Business GP for", "format": "html"})
    business_gp_subtitle = RichTextField(default={"content": "complex systems — digital and living.", "format": "html"})
    business_gp_description = RichTextField(default={"content": "We listen to the whole organisation, solve with structure and insight, and optimise so you can grow with confidence.", "format": "html"})
    business_gp_button_text = RichTextField(default={"content": "Contact Us", "format": "html"})
    business_gp_image = models.CharField(max_length=500, default="/images/handshake.png")
    
    # Services Overview Section
    services_overview_title = RichTextField(default={"content": "SERVICES OVERVIEW", "format": "html"})
    
    service_1_title = RichTextField(default={"content": "Strategic Advisory & Compliance", "format": "html"})
    service_1_description = RichTextField(default={"content": "We deliver clarity to complexity. From regulatory and sustainability frameworks to biotechnology and compliance consulting, our experts guide clients through evolving landscapes with confidence. Our approach combines deep technical insight with strategic foresight, ensuring every initiative is compliant, sustainable, and built for growth.", "format": "html"})
    service_1_image = models.CharField(max_length=500, default="")
    service_1_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    service_2_title = RichTextField(default={"content": "Operational Systems & Infrastructure", "format": "html"})
    service_2_description = RichTextField(default={"content": "We design, build and streamline the systems that power modern organizations. Whether it's creating SOPs, structuring onboarding workflows, or coordinating complex office setups, we turn operations into well- functioning ecosystems. Our trusted network of builders, finishers, and tech specialists delivers reliability from planning to execution.", "format": "html"})
    service_2_image = models.CharField(max_length=500, default="")
    service_2_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    # Data Intelligence Section
    data_intelligence_title = RichTextField(default={"content": "Data Intelligence & Concierge Solutions", "format": "html"})
    data_intelligence_description = RichTextField(default={"content": "Insight meets adaptability. We help organizations turn data into decisions through advanced analytics, KPI dashboards, and predictive modeling. Alongside our concierge division, we offer personalized support and problem-solving — delivering smart, human solutions for both business and lifestyle needs with precision and discretion.", "format": "html"})
    data_intelligence_image = models.CharField(max_length=500, default="")
    data_intelligence_button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Services Page Content"
        verbose_name_plural = "Services Page Content"
    
    def __str__(self):
        return f"Services Page - {self.hero_title}"


class ResourcesBlogsPage(Audit):
    """Resources & Blogs page content management"""
    
    # Hero Section
    hero_title = RichTextField(default={"content": "Resources / Blogs", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "", "format": "html"})
    
    # Blog Cards (4 cards)
    blog_card_1_title = RichTextField(default={"content": "Mobile Apps & PWAs for Maltese Insurers: Boost Engagement | Born Digital", "format": "html"})
    blog_card_1_category = RichTextField(default={"content": "Article", "format": "html"})
    blog_card_1_image = models.CharField(max_length=500, default="/images/image.png")
    
    blog_card_2_title = RichTextField(default={"content": "Mobile Apps & PWAs for Maltese Insurers: Boost Engagement | Born Digital", "format": "html"})
    blog_card_2_category = RichTextField(default={"content": "Article", "format": "html"})
    blog_card_2_image = models.CharField(max_length=500, default="/images/image.png")
    
    blog_card_3_title = RichTextField(default={"content": "Mobile Apps & PWAs for Maltese Insurers: Boost Engagement | Born Digital", "format": "html"})
    blog_card_3_category = RichTextField(default={"content": "Article", "format": "html"})
    blog_card_3_image = models.CharField(max_length=500, default="/images/image.png")
    
    blog_card_4_title = RichTextField(default={"content": "Mobile Apps & PWAs for Maltese Insurers: Boost Engagement | Born Digital", "format": "html"})
    blog_card_4_category = RichTextField(default={"content": "Article", "format": "html"})
    blog_card_4_image = models.CharField(max_length=500, default="/images/image.png")
    
    # Admin Tips Section
    admin_tips_title = RichTextField(default={"content": "Admin Tips", "format": "html"})
    
    tip_1_number = models.CharField(max_length=500, default="01")
    tip_1_title = RichTextField(default={"content": "", "format": "html"})
    tip_1_description = RichTextField(default={"content": "", "format": "html"})
    
    tip_2_number = models.CharField(max_length=500, default="02")
    tip_2_title = RichTextField(default={"content": "", "format": "html"})
    tip_2_description = RichTextField(default={"content": "", "format": "html"})
    
    tip_3_number = models.CharField(max_length=500, default="03")
    tip_3_title = RichTextField(default={"content": "", "format": "html"})
    tip_3_description = RichTextField(default={"content": "", "format": "html"})
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Resources & Blogs Page Content"
        verbose_name_plural = "Resources & Blogs Page Content"
    
    def __str__(self):
        return f"Resources & Blogs Page - {self.hero_title}"


class LegacyPolicyPage(Audit):
    """Legacy & Policy page content management"""
    
    # Hero Section
    hero_title = RichTextField(default={"content": "Legacy & Policy", "format": "html"})
    hero_description = RichTextField(default={"content": "", "format": "html"})
    
    # Policy Items
    policy_item_1_number = models.CharField(max_length=500, default="01")
    policy_item_1_description = RichTextField(default={"content": "", "format": "html"})
    
    policy_item_2_number = models.CharField(max_length=500, default="02")
    policy_item_2_description = RichTextField(default={"content": "", "format": "html"})
    
    policy_item_3_number = models.CharField(max_length=500, default="03")
    policy_item_3_description = RichTextField(default={"content": "", "format": "html"})
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Legacy & Policy Page Content"
        verbose_name_plural = "Legacy & Policy Page Content"
    
    def __str__(self):
        return f"Legacy & Policy Page - {self.hero_title}"


class ContactPage(Audit):
    """Contact page content management"""
    
    # Hero Section
    hero_title = RichTextField(default={"content": "Contact Us", "format": "html"})
    
    # Contact Information
    contact_info_title = RichTextField(default={"content": "Contact Information", "format": "html"})
    contact_info_subtitle = RichTextField(default={"content": "Say something to start a live chat!", "format": "html"})
    
    phone_number = models.CharField(max_length=500, default="")
    email_address = models.EmailField(max_length=500, default="")
    address = RichTextField(default={"content": "132 Dartmouth Street Boston, Massachusetts 02156 United States", "format": "html"})
    
    # Form Labels
    first_name_label = RichTextField(default={"content": "First Name", "format": "html"})
    last_name_label = RichTextField(default={"content": "Last Name", "format": "html"})
    email_label = RichTextField(default={"content": "Email", "format": "html"})
    phone_label = RichTextField(default={"content": "Phone Number", "format": "html"})
    subject_label = RichTextField(default={"content": "Select Subject?", "format": "html"})
    message_label = RichTextField(default={"content": "Message", "format": "html"})
    
    # Form Placeholders
    first_name_placeholder = RichTextField(default={"content": "", "format": "html"})
    last_name_placeholder = RichTextField(default={"content": "", "format": "html"})
    email_placeholder = RichTextField(default={"content": "", "format": "html"})
    phone_placeholder = RichTextField(default={"content": "", "format": "html"})
    message_placeholder = RichTextField(default={"content": "Write your message...", "format": "html"})
    
    # Subject Options
    subject_option_1 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    subject_option_2 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    subject_option_3 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    subject_option_4 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    
    # Submit Button
    submit_button_text = RichTextField(default={"content": "Send Message", "format": "html"})
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Contact Page Content"
        verbose_name_plural = "Contact Page Content"
    
    def __str__(self):
        return f"Contact Page - {self.hero_title}"


class SiteSettings(Audit):
    """Global site settings"""
    
    site_name = RichTextField(default={"content": "ORR", "format": "html"})
    site_tagline = RichTextField(default={"content": "", "format": "html"}, blank=True)
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    favicon = models.ImageField(upload_to='branding/', blank=True, null=True)
    
    # Colors
    primary_color = models.CharField(max_length=500, default="#007bff")
    secondary_color = models.CharField(max_length=500, default="#6c757d")
    accent_color = models.CharField(max_length=500, default="#28a745")
    
    # Footer
    footer_text = RichTextField(default={"content": "", "format": "html"}, blank=True)
    copyright_text = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    # Analytics
    google_analytics_id = models.CharField(max_length=500, blank=True)
    facebook_pixel_id = models.CharField(max_length=500, blank=True)
    
    # Legal
    privacy_policy_url = models.URLField(max_length=500, blank=True)
    terms_of_service_url = models.URLField(max_length=500, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return f"{self.site_name} Settings"


# NEW COMPREHENSIVE CMS MODELS

class HowWeOperatePageContent(Audit):
    """How We Operate page content management"""
    
    hero_title = RichTextField(default={"content": "How We Operate", "format": "html"})
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "How We Operate Page Content"
        verbose_name_plural = "How We Operate Page Content"
    
    def __str__(self):
        return f"How We Operate - {self.hero_title}"


class ProcessStep(Audit):
    """Process steps for How We Operate page"""
    
    step_number = models.CharField(max_length=500, default="01")
    title = RichTextField(default={"content": "Step Title", "format": "html"})
    subtitle = RichTextField(default={"content": "", "format": "html"}, blank=True)
    description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet1 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet2 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet3 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet4 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet5 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet6 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet7 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet8 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    bullet9 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    wordbreak = RichTextField(default={"content": "", "format": "html"}, blank=True)
    description1 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    description2 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    description3 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    description4 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    image_url = models.URLField(max_length=500, default="")
    button_text = RichTextField(default={"content": "", "format": "html"}, blank=True)
    button_text2 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    button_text3 = RichTextField(default={"content": "", "format": "html"}, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Process Step"
        verbose_name_plural = "Process Steps"
    
    def __str__(self):
        return f"{self.step_number} - {self.title}"


class ServicesPageContent(Audit):
    """Services page content management"""
    
    hero_title = RichTextField(default={"content": "ORR Solutions - Listen. Solve. Optimise.", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "We treat your organisation as a whole system — digital, regulatory, and living. We listen first, then design the right mix of advisory, systems, AI, and on-the-ground projects so you can move better and grow smarter too.", "format": "html"})
    pillars_title = RichTextField(default={"content": "The Three Pillars", "format": "html"})
    business_gp_title = RichTextField(default={"content": "ORR is your Business GP for", "format": "html"})
    business_gp_subtitle = RichTextField(default={"content": "complex systems — digital and living.", "format": "html"})
    business_gp_description = RichTextField(default={"content": "We listen to the whole organisation, solve with structure and insight, and optimise so you can grow with confidence.", "format": "html"})
    business_gp_button_text = RichTextField(default={"content": "Contact Us", "format": "html"})
    business_gp_image = models.CharField(max_length=500, default="/images/handshake.png")
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Services Page Content"
        verbose_name_plural = "Services Page Content"
    
    def __str__(self):
        return f"Services Page - {self.hero_title}"


class ServiceStage(Audit):
    """Service stages for Services page"""
    
    stage_number = models.PositiveIntegerField(default=1)
    title = RichTextField(default={"content": "STAGE 1 - DISCOVER", "format": "html"})
    subtitle = RichTextField(default={"content": "Listen.", "format": "html"})
    description = RichTextField(default={"content": "Stage description", "format": "html"})
    focus_content = RichTextField(default={"content": "Focus points", "format": "html"})
    button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Service Stage"
        verbose_name_plural = "Service Stages"
    
    def __str__(self):
        return f"Stage {self.stage_number} - {self.title}"


class ServicePillar(Audit):
    """Service pillars for Services page"""
    
    title = RichTextField(default={"content": "Digital Systems, Automation & AI", "format": "html"})
    description = RichTextField(default={"content": "Pillar description", "format": "html"})
    button_text = RichTextField(default={"content": "Learn More", "format": "html"})
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Service Pillar"
        verbose_name_plural = "Service Pillars"
    
    def __str__(self):
        return self.title


class ResourcesBlogsPageContent(Audit):
    """Resources & Blogs page content management"""
    
    hero_title = RichTextField(default={"content": "Resources & Client Portal", "format": "html"})
    hero_description1 = RichTextField(default={"content": "Your digital HQ for business clarity, timelines, and real-time status. This isn't a traditional blog.", "format": "html"})
    hero_description2 = RichTextField(default={"content": "Our resources are organized around the ORR client portal — a dashboard where you can read FAQs, download material, request meetings, and chat with a live operator or consultant.", "format": "html"})
    hero_description3 = RichTextField(default={"content": "Instead of scattered articles, you get structured guidance that follows our live project — following blogs have insight, how-to — and real-time alerts. Everything is organized around live project management, AI marketing systems & implementation.", "format": "html"})
    hero_button1_text = RichTextField(default={"content": "Request access to the client portal", "format": "html"})
    hero_button2_text = RichTextField(default={"content": "Learn how we operate", "format": "html"})
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Resources & Blogs Page Content"
        verbose_name_plural = "Resources & Blogs Page Content"
    
    def __str__(self):
        return f"Resources & Blogs Page - {self.hero_title}"


class ContentCard(Audit):
    """Content cards for Resources & Blogs page"""
    
    badge = RichTextField(default={"content": "Blog", "format": "html"})
    title = RichTextField(default={"content": "Content Title", "format": "html"})
    card_slug = models.SlugField(max_length=500, unique=True, blank=True, null=True) 
    content = models.JSONField(default=list)  # Array of content strings
    image_url = models.URLField(max_length=500, default="https://res.cloudinary.com/depeqzb6z/image/upload/v1765559589/21743692_6495306_uay57y.jpg")
    button1_text = RichTextField(default={"content": "", "format": "html"}, blank=True)
    button2_text = RichTextField(default={"content": "", "format": "html"}, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["order"]
        verbose_name = "Content Card"
        verbose_name_plural = "Content Cards"
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.card_slug and hasattr(self.title, 'get') and self.title.get('content'):
            from django.utils.text import slugify
            base_slug = slugify(self.title['content'][:50])  # Limit to 50 chars for slug generation
            slug = base_slug
            counter = 1
            while ContentCard.objects.filter(card_slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.card_slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        if hasattr(self.title, 'get') and self.title.get('content'):
            return self.title['content']
        return str(self.title)


class LegalPolicyPageContent(Audit):
    """Legal & Policy page content management"""
    
    hero_title = RichTextField(default={"content": "Legacy & Policy", "format": "html"})
    hero_description = RichTextField(default={"content": "Lorem ipsm jgdu mplexity. From regulatory and sustainability frameworks to biotechnology and compliance consulting, our experts guide clients through evolving legal, scientific, and operational standards. Our approach combines deep technical insight with strategic foresight — ensuring every initiative is compliant, sustainable, and built for growth.", "format": "html"})
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Legal & Policy Page Content"
        verbose_name_plural = "Legal & Policy Page Content"
    
    def __str__(self):
        return f"Legal & Policy Page - {self.hero_title}"


class PolicyItem(Audit):
    """Policy items for Legal & Policy page"""
    
    number = models.CharField(max_length=500, default="01")
    description = RichTextField(default={"content": "Policy description", "format": "html"})
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Policy Item"
        verbose_name_plural = "Policy Items"
    
    def __str__(self):
        return f"{self.number} - Policy Item"


class ContactPageContent(Audit):
    """Contact page content management"""
    
    hero_title = RichTextField(default={"content": "Contact Us", "format": "html"})
    contact_info_title = RichTextField(default={"content": "Contact Information", "format": "html"})
    contact_info_subtitle = RichTextField(default={"content": "Say something to start a live chat!", "format": "html"})
    phone_number = models.CharField(max_length=500, default="")
    email_address = models.EmailField(max_length=500, default="")
    address = RichTextField(default={"content": "132 Dartmouth Street Boston, Massachusetts 02156 United States", "format": "html"})
    first_name_label = RichTextField(default={"content": "First Name", "format": "html"})
    last_name_label = RichTextField(default={"content": "Last Name", "format": "html"})
    email_label = RichTextField(default={"content": "Email", "format": "html"})
    phone_label = RichTextField(default={"content": "Phone Number", "format": "html"})
    subject_label = RichTextField(default={"content": "Select Subject?", "format": "html"})
    message_label = RichTextField(default={"content": "Message", "format": "html"})
    first_name_placeholder = RichTextField(default={"content": "", "format": "html"})
    last_name_placeholder = RichTextField(default={"content": "", "format": "html"})
    email_placeholder = RichTextField(default={"content": "", "format": "html"})
    phone_placeholder = RichTextField(default={"content": "", "format": "html"})
    message_placeholder = RichTextField(default={"content": "Write your message...", "format": "html"})
    subject_option_1 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    subject_option_2 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    subject_option_3 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    subject_option_4 = RichTextField(default={"content": "General Inquiry", "format": "html"})
    submit_button_text = RichTextField(default={"content": "Send Message", "format": "html"})
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Contact Page Content"
        verbose_name_plural = "Contact Page Content"
    
    def __str__(self):
        return f"Contact Page - {self.hero_title}"


# NEW SERVICE PILLAR PAGES

class StrategicAdvisoryPageContent(Audit):
    """Strategic Advisory & Compliance page content management"""
    
    hero_title = RichTextField(default={"content": "Strategic Advisory & Compliance", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "We deliver clarity to complexity. From regulatory and sustainability frameworks to biotechnology and compliance consulting, our experts guide clients through evolving landscapes with confidence.", "format": "html"})
    hero_description = RichTextField(default={"content": "Our approach combines deep technical insight with strategic foresight, ensuring every initiative is compliant, sustainable, and built for growth.", "format": "html"})
    hero_image = models.URLField(max_length=500, default="")
    
    # Services Section
    services_title = RichTextField(default={"content": "Our Strategic Services", "format": "html"})
    service_1_title = RichTextField(default={"content": "Regulatory Compliance", "format": "html"})
    service_1_description = RichTextField(default={"content": "Navigate complex regulatory frameworks with confidence", "format": "html"})
    service_2_title = RichTextField(default={"content": "ESG & Sustainability", "format": "html"})
    service_2_description = RichTextField(default={"content": "Build sustainable business practices that drive growth", "format": "html"})
    service_3_title = RichTextField(default={"content": "Risk Management", "format": "html"})
    service_3_description = RichTextField(default={"content": "Identify and mitigate business risks proactively", "format": "html"})
    
    # Process Section
    process_title = RichTextField(default={"content": "Our Strategic Process", "format": "html"})
    process_subtitle = RichTextField(default={"content": "Listen . Solve . Optimize", "format": "html"})
    process_description = RichTextField(default={"content": "Like your Business GP, we diagnose compliance challenges and prescribe strategic solutions tailored to your organization's unique context.", "format": "html"})
    process_step_1_title = RichTextField(default={"content": "Listen & Report", "format": "html"})
    process_step_1_subtitle = RichTextField(default={"content": "(Initial Discovery)", "format": "html"})
    process_step_1 = RichTextField(default={"content": "We start with a focused initial meeting to understand your compliance challenges, regulatory environment, and strategic objectives.", "format": "html"})
    process_step_2_title = RichTextField(default={"content": "Decide: Document or Partnership", "format": "html"})
    process_step_2 = RichTextField(default={"content": "Once you receive the report, you choose your path forward: Use the report independently or engage ORR for ongoing implementation support.", "format": "html"})
    process_step_3_title = RichTextField(default={"content": "Optimize (For Clients Who Continue)", "format": "html"})
    process_step_3 = RichTextField(default={"content": "For clients who choose ongoing partnership, we move into implementation and optimization.", "format": "html"})
    process_step_4 = RichTextField(default={"content": "With systems live, we provide continuous monitoring, regular reviews, and proactive adjustments to ensure your compliance strategies evolve with changing regulations and business needs.", "format": "html"})
    process_step_4_title = RichTextField(default={"content": "Grow", "format": "html"})
    # Network Section
    network_title = RichTextField(default={"content": "The ORR Network Advantage", "format": "html"})
    network_description = RichTextField(default={"content": "Complex compliance challenges require diverse expertise. We activate our global network of specialists to deliver comprehensive solutions.", "format": "html"})
    network_cards = models.JSONField(default=list)
    
    # Digital Solutions Section
    digital_title = RichTextField(default={"content": "Digital Solutions for", "format": "html"})
    digital_subtitle = RichTextField(default={"content": "Compliance Management", "format": "html"})
    digital_description = RichTextField(default={"content": "We don't just advise — we build digital infrastructure to operationalize compliance:", "format": "html"})
    digital_image_alt = RichTextField(default={"content": "Network visualization showing connected nodes and data flows", "format": "html"})
    digital_who_is_this_for = models.JSONField(default=list)
    digital_features = models.JSONField(default=list)
    
    # Case Example Section
    case_challenge = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_solution = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_result = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_image_alt = RichTextField(default={"content": "Business documents and reports on a desk", "format": "html"})
    
    # CTA Section
    cta_title = RichTextField(default={"content": "Ready to Transform Your Strategy?", "format": "html"})
    cta_description = RichTextField(default={"content": "Let's discuss how our strategic advisory services can help your organization thrive.", "format": "html"})
    cta_button_text = RichTextField(default={"content": "Get Started", "format": "html"})
    
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Strategic Advisory Page Content"
        verbose_name_plural = "Strategic Advisory Page Content"
    
    def __str__(self):
        return f"Strategic Advisory - {self.hero_title}"


class OperationalSystemsPageContent(Audit):
    """Operational Systems & Infrastructure page content management"""
    
    hero_title = RichTextField(default={"content": "Operational Systems & Infrastructure", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "We design, build and streamline the systems that power modern organizations. Whether it's creating SOPs, structuring workflows, or coordinating complex setups.", "format": "html"})
    hero_description = RichTextField(default={"content": "We turn operations into well-functioning ecosystems. Our trusted network of builders and tech specialists delivers reliability from planning to execution.", "format": "html"})
    hero_image = models.URLField(max_length=500, default="")
    
    # Services Section
    services_title = RichTextField(default={"content": "Our Operational Services", "format": "html"})
    service_1_title = RichTextField(default={"content": "Process Optimization", "format": "html"})
    service_1_description = RichTextField(default={"content": "Streamline workflows and eliminate operational bottlenecks", "format": "html"})
    service_2_title = RichTextField(default={"content": "System Integration", "format": "html"})
    service_2_description = RichTextField(default={"content": "Connect your tools and platforms for seamless operations", "format": "html"})
    service_3_title = RichTextField(default={"content": "Infrastructure Setup", "format": "html"})
    service_3_description = RichTextField(default={"content": "Build robust operational foundations that scale", "format": "html"})
    
    # Process Section
    process_title = RichTextField(default={"content": "Our Implementation Process", "format": "html"})
    process_description = RichTextField(default={"content": "Just like your Business GP, we follow a systematic diagnostic and treatment approach to restore operational health.", "format": "html"})
    process_step_1_title = RichTextField(default={"content": "Listen (Assess)", "format": "html"})
    process_step_1 = RichTextField(default={"content": "Current State Analysis", "format": "html"})
    process_step_2_title = RichTextField(default={"content": "Solve (Design & Implement)", "format": "html"})
    process_step_2 = RichTextField(default={"content": "System Design", "format": "html"})
    process_step_3_title = RichTextField(default={"content": "Optimize (Refine & Evolve)", "format": "html"})
    process_step_3 = RichTextField(default={"content": "Implementation & Testing", "format": "html"})
    process_step_4_title = RichTextField(default={"content": "Monitor (Sustain)", "format": "html"})
    process_step_4 = RichTextField(default={"content": "Ongoing Support", "format": "html"})
    # Case Example Section
    case_challenge = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_solution = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_result = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_image_alt = RichTextField(default={"content": "Business documents and reports on a desk", "format": "html"})
    
    # CTA Section
    cta_title = RichTextField(default={"content": "Ready to Optimize Your Operations?", "format": "html"})
    cta_description = RichTextField(default={"content": "Let's build systems that work as hard as your team does.", "format": "html"})
    cta_button_text = RichTextField(default={"content": "Get Started", "format": "html"})
    
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Operational Systems Page Content"
        verbose_name_plural = "Operational Systems Page Content"
    
    def __str__(self):
        title_text = self.hero_title.get('content', '') if isinstance(self.hero_title, dict) else str(self.hero_title)
        return f"Operational Systems - {title_text}"


class LivingSystemsPageContent(Audit):
    """Living Systems & Regeneration page content management"""
    
    hero_title = RichTextField(default={"content": "Living Systems & Regeneration", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "Support for land, water, species, and ecosystems — from production systems to restoration and incident response.", "format": "html"})
    hero_description = RichTextField(default={"content": "We help organizations integrate regenerative practices that benefit both business outcomes and environmental health.", "format": "html"})
    hero_image = models.URLField(max_length=500, default="")
    
    # Services Section
    services_title = RichTextField(default={"content": "Our Regenerative Services", "format": "html"})
    service_1_title = RichTextField(default={"content": "Ecosystem Restoration", "format": "html"})
    service_1_description = RichTextField(default={"content": "Restore and regenerate natural systems for long-term sustainability", "format": "html"})
    service_2_title = RichTextField(default={"content": "Sustainable Production", "format": "html"})
    service_2_description = RichTextField(default={"content": "Design production systems that work with natural processes", "format": "html"})
    service_3_title = RichTextField(default={"content": "Environmental Monitoring", "format": "html"})
    service_3_description = RichTextField(default={"content": "Track and measure environmental impact and recovery", "format": "html"})
    
    # Process Section
    process_title = RichTextField(default={"content": "Our Regenerative Approach", "format": "html"})
    process_description = RichTextField(default={"content": "At the heart of our work, we take a systems approach to understanding and regenerating living systems. We observe the current state, design regenerative solutions, and implement systems that restore ecological health while creating economic value.", "format": "html"})
    process_step_1 = RichTextField(default={"content": "Ecosystem Assessment", "format": "html"})
    process_step_2 = RichTextField(default={"content": "Regenerative Design", "format": "html"})
    process_step_3 = RichTextField(default={"content": "Implementation & Monitoring", "format": "html"})
    process_step_4 = RichTextField(default={"content": "Adaptive Management", "format": "html"})
    
    # Case Example Section
    case_challenge = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_solution = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_result = RichTextField(default={"content": "", "format": "html"}, blank=True)
    case_image_alt = RichTextField(default={"content": "Regenerative agriculture landscape showing restored soil and biodiversity", "format": "html"})
    
    # CTA Section
    cta_title = RichTextField(default={"content": "Ready to Regenerate Your Impact?", "format": "html"})
    cta_description = RichTextField(default={"content": "Let's create systems that restore while they produce.", "format": "html"})
    cta_button_text = RichTextField(default={"content": "Get Started", "format": "html"})
    
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Living Systems Page Content"
        verbose_name_plural = "Living Systems Page Content"
    
    def __str__(self):
        title_text = self.hero_title.get('content', '') if isinstance(self.hero_title, dict) else str(self.hero_title)
        return f"Living Systems - {title_text}"

class CustomLandingPage(Audit):
    """Dynamic custom landing pages"""
    
    title = models.CharField(max_length=200, help_text="Internal name for this landing page")
    slug = models.SlugField(max_length=200, unique=True)
    
    # Hero Section
    hero_title = RichTextField(default={"content": "Welcome", "format": "html"})
    hero_subtitle = RichTextField(default={"content": "Discover our services", "format": "html"}, blank=True)
    hero_image = models.URLField(max_length=500, blank=True)
    
    # Content Sections (Flexible)
    section_1_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    section_1_content = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    section_2_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    section_2_content = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    section_3_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    section_3_content = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    # CTA Section
    cta_title = RichTextField(default={"content": "Ready to get started?", "format": "html"}, blank=True)
    cta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    cta_button_text = RichTextField(default={"content": "Get Started", "format": "html"}, blank=True)
    cta_button_link = models.CharField(max_length=500, blank=True)
    
    # SEO
    meta_title = RichTextField(default={"content": "", "format": "html"}, blank=True)
    meta_description = RichTextField(default={"content": "", "format": "html"}, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Custom Landing Page"
        verbose_name_plural = "Custom Landing Pages"
    
    def __str__(self):
        return self.title