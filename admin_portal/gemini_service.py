"""
Gemini AI Service — Central AI integration for ORR Solutions Platform.

Provides all AI-powered features using Google Gemini 2.0 Flash.
All methods include fallback handling if the API is unavailable.
"""

import json
import logging
from typing import Dict, List, Optional

from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)

# Lazy-loaded client
_genai_client = None


def _get_client():
    """Get or create the Gemini client (lazy singleton)."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    try:
        from google import genai

        api_key = config("GEMINI_API_KEY", default="")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set — AI features disabled")
            return None

        _genai_client = genai.Client(api_key=api_key)
        return _genai_client
    except ImportError:
        logger.error("google-genai package not installed. Run: pip install google-genai")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_ID = "gemini-3.6-flash"

ORR_SYSTEM_CONTEXT = """You are an AI assistant for ORR Solutions, a professional consultancy firm based in Malta.

ABOUT ORR SOLUTIONS:
ORR Solutions is a forward-thinking consultancy focused on structural, digital, and environmental transformation. We blend traditional strategy with cutting-edge technology and regenerative practices.
We focus on sustainable growth, operational resilience, and compliance.

CORE SERVICE PILLARS:
1. **Strategy Advisory & Compliance** — Regulatory guidance, governance frameworks, strategic planning, licensing, risk management, ESG advisory.
2. **Operational Systems & Infrastructure** — Process optimisation, IT systems, digital transformation, data pipelines, workflow automation, cybersecurity basics.
3. **Living Systems Regeneration** — Sustainability, circular economy, environmental compliance, agronomic advisory, biodiversity, regenerative agriculture.

METHODOLOGY (The 5D Journey):
- Discover: Initial scoping and understanding.
- Diagnose: Deep analysis and risk assessment.
- Design: Creating tailored, actionable frameworks.
- Deploy: Implementation and change management.
- Grow: Ongoing support and scaling.

AI PERSONA / TONE:
Always adapt your response to the user's preferred persona if provided. Otherwise, maintain a professional, warm, and knowledgeable tone. Be concise but thorough.

STRICT RULES:
Never fabricate specific legal, financial, or regulatory advice — always recommend consulting with the relevant ORR specialist instead."""


# ---------------------------------------------------------------------------
# Core AI Methods
# ---------------------------------------------------------------------------


def generate_text(prompt: str, system_context: str = "") -> str:
    """
    Generate general text using Gemini AI model with fallback handling.
    """
    client = _get_client()
    if not client:
        logger.warning("Gemini client unavailable for generate_text")
        return ""

    full_context = f"{ORR_SYSTEM_CONTEXT}\n\n{system_context}".strip() if system_context else ORR_SYSTEM_CONTEXT

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config={
                "system_instruction": full_context,
                "temperature": 0.7,
            }
        )
        return response.text.strip() if response and hasattr(response, 'text') else ""
    except Exception as e:
        logger.error(f"Gemini generate_text failed: {e}")
        return ""


class GeminiService:
    """
    Class interface for Gemini AI Services.
    Enables instantiation (gemini = GeminiService()) and method invocation across views.
    """
    def generate_text(self, prompt: str, system_context: str = "") -> str:
        return generate_text(prompt, system_context)

    def generate_smart_reply(self, *args, **kwargs):
        return generate_smart_reply(*args, **kwargs)

    def generate_project_proposal(self, *args, **kwargs):
        return generate_project_proposal(*args, **kwargs)

    def generate_meeting_prep(self, *args, **kwargs):
        return generate_meeting_prep(*args, **kwargs)

    def summarize_document(self, *args, **kwargs):
        return summarize_document(*args, **kwargs)

    def generate_client_insights(self, *args, **kwargs):
        return generate_client_insights(*args, **kwargs)

    def analyze_onboarding(self, *args, **kwargs):
        return analyze_onboarding(*args, **kwargs)

    def chat(self, *args, **kwargs):
        return chat(*args, **kwargs)

    def generate_dashboard_insights(self, *args, **kwargs):
        return generate_dashboard_insights(*args, **kwargs)



def generate_smart_reply(
    ticket_subject: str,
    ticket_description: str,
    client_name: str = "",
    client_stage: str = "",
    client_pillar: str = "",
    previous_messages: Optional[List[str]] = None,
) -> str:
    """
    Generate a contextual, intelligent reply for a support ticket.

    Returns a professional response string, or a sensible fallback.
    """
    client = _get_client()
    if not client:
        return _fallback_ticket_reply(client_name)

    context_parts = [f"Client: {client_name}"] if client_name else []
    if client_stage:
        context_parts.append(f"Stage: {client_stage}")
    if client_pillar:
        context_parts.append(f"Primary Pillar: {client_pillar}")

    history_text = ""
    if previous_messages:
        history_text = "\n\nPrevious conversation:\n" + "\n".join(
            f"- {msg}" for msg in previous_messages[-5:]
        )

    prompt = f"""{ORR_SYSTEM_CONTEXT}

You are responding to a client support ticket. Generate a professional, empathetic, and helpful acknowledgement reply.

{" | ".join(context_parts)}

Ticket Subject: {ticket_subject}
Ticket Description: {ticket_description}
{history_text}

Requirements:
- Acknowledge the client's concern specifically (don't use generic phrases)
- Reference ORR's relevant service area if applicable
- Set realistic expectations for follow-up timing
- Keep the reply between 2-4 sentences
- Sign off as "ORR Solutions Team"
- Do NOT make up specific deadlines or promises"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Error in generate_smart_reply: {e}")
        return _fallback_ticket_reply(client_name)


def generate_project_proposal(
    project_scope: str,
    project_deliverables: str,
    consultant_feedback: str,
    client_name: str,
    industry: str
) -> str:
    """
    Generate a formal project proposal / draft document based on PM scope and Consultant feedback.
    """
    client = _get_client()
    if not client:
        return "Proposal could not be generated. AI service unavailable."

    prompt = f"""{ORR_SYSTEM_CONTEXT}

Task: Generate a formal project proposal based on the following details.

Client: {client_name}
Industry: {industry}

Project Scope (from PM):
{project_scope}

Project Deliverables (from PM):
{project_deliverables}

Consultant Feedback / Approach:
{consultant_feedback}

Format the output as a professional business proposal in markdown format. 
Include the following sections:
- Executive Summary
- Project Objectives & Scope
- Proposed Technical Approach (incorporating the consultant's feedback)
- Deliverables & Timeline
- Investment / Cost Estimate (based on consultant feedback if provided)

Keep the tone highly professional, aligning with ORR Solutions' standards.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Error in generate_project_proposal: {e}")
        return "Error generating proposal document."


def _fallback_ticket_reply(client_name: str) -> str:
    return f"Dear {client_name or 'Client'}, thank you for contacting ORR Solutions. We have received your query and a specialist will get back to you shortly."


def generate_meeting_prep(
    meeting_type: str,
    client_name: str,
    client_company: str = "",
    client_stage: str = "",
    client_pillar: str = "",
    agenda: str = "",
    goals: str = "",
    pain_points: str = "",
    basic_context: str = "",
) -> Dict:
    """
    Generate an AI meeting preparation brief.

    Returns a dict with keys: summary, talking_points, suggested_questions, recommendations.
    """
    client = _get_client()
    if not client:
        return _fallback_meeting_prep(meeting_type, client_name)

    prompt = f"""{ORR_SYSTEM_CONTEXT}

Generate a concise meeting preparation brief for an upcoming consultation.

Meeting Type: {meeting_type}
Client: {client_name} ({client_company})
Client Stage: {client_stage or 'Not specified'}
Primary Pillar: {client_pillar or 'Not specified'}
Agenda: {agenda or 'Not specified'}
Goals: {goals or 'Not specified'}
Pain Points: {pain_points or 'Not specified'}
Context: {basic_context or 'Not specified'}

Return a JSON object with these exact keys:
- "summary": A 2-3 sentence overview of what to expect and prepare for (string)
- "talking_points": Array of 4-5 key discussion topics (array of strings)
- "suggested_questions": Array of 3-4 questions to ask the client (array of strings)
- "recommendations": Array of 2-3 action items to prepare before the meeting (array of strings)

Return ONLY valid JSON, no markdown formatting."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        return json.loads(text)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Gemini meeting prep failed: {e}")
        return _fallback_meeting_prep(meeting_type, client_name)


def summarize_document(
    title: str,
    content: str,
    max_length: int = 200,
) -> Dict:
    """
    Summarize a document/content piece.

    Returns dict with keys: summary, key_points, suggested_tags.
    """
    client = _get_client()
    if not client:
        return {"summary": content[:max_length] + "...", "key_points": [], "suggested_tags": []}

    # Truncate very long content to avoid token limits
    truncated = content[:8000] if len(content) > 8000 else content

    prompt = f"""{ORR_SYSTEM_CONTEXT}

Summarize this document for ORR Solutions platform users.

Title: {title}
Content: {truncated}

Return a JSON object with these exact keys:
- "summary": A concise summary in {max_length} characters or less (string)
- "key_points": Array of 3-5 key takeaways (array of strings)
- "suggested_tags": Array of 2-4 relevant category tags (array of strings)

Return ONLY valid JSON, no markdown formatting."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini document summary failed: {e}")
        return {"summary": content[:max_length] + "...", "key_points": [], "suggested_tags": []}


def generate_client_insights(
    client_name: str,
    client_company: str,
    stage: str,
    pillar: str,
    total_meetings: int = 0,
    total_tickets: int = 0,
    total_documents: int = 0,
    recent_activity: str = "",
    role: str = "",
    internal_notes: str = "",
    secondary_pillars: list = None,
) -> Dict:
    """
    Generate AI-powered insights about a client's journey and engagement.

    Returns dict with keys: health_score, insights, recommendations, risk_flags.
    """
    client = _get_client()
    if not client:
        return _fallback_client_insights()

    secondary_pillars_str = ", ".join(secondary_pillars) if secondary_pillars else "None"

    prompt = f"""{ORR_SYSTEM_CONTEXT}

Analyze the following client engagement data and provide actionable insights.

Client: {client_name} ({client_company})
Role/Position: {role or 'Not specified'}
Current Stage: {stage}
Primary Pillar: {pillar}
Secondary Pillars: {secondary_pillars_str}
Total Meetings: {total_meetings}
Total Tickets: {total_tickets}
Total Documents: {total_documents}
Recent Activity: {recent_activity or 'No recent activity recorded'}
Internal Notes/Context: {internal_notes or 'No specific internal notes provided'}

Using this comprehensive personal, company, and engagement data, return a JSON object with these exact keys:
- "health_score": A score from 1-100 representing overall engagement health (integer)
- "insights": Array of 2-3 observations about the client's engagement pattern based on their role, company, and notes (array of strings)
- "recommendations": Array of 2-3 actionable next steps for the ORR team to nurture this client (array of strings)
- "risk_flags": Array of 0-2 potential concerns to address (array of strings)

Return ONLY valid JSON, no markdown formatting."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini client insights failed: {e}")
        return _fallback_client_insights()


def analyze_onboarding(
    user_type: str,
    project_stage: str,
    jurisdiction: str,
    orr_pillars: list,
    challenges: list,
    has_active_project: str,
    project_description: str = "",
    communication_tone: str = "",
) -> Dict:
    """
    Analyze onboarding questionnaire responses and generate personalized recommendations.

    Returns dict with keys: recommended_pillar, roadmap_summary, immediate_actions, ai_notes.
    """
    client = _get_client()
    if not client:
        return _fallback_onboarding_analysis(orr_pillars)

    prompt = f"""{ORR_SYSTEM_CONTEXT}

A new client has completed their onboarding questionnaire. Analyze their responses and provide personalized recommendations.

User Type: {user_type}
Project Stage: {project_stage}
Jurisdiction: {jurisdiction}
Selected ORR Pillars: {', '.join(orr_pillars) if orr_pillars else 'None selected'}
Key Challenges: {', '.join(challenges) if challenges else 'None specified'}
Active Project: {has_active_project}
Project Description: {project_description or 'Not provided'}
Preferred Communication: {communication_tone or 'Not specified'}

Return a JSON object with these exact keys:
- "recommended_pillar": The most suitable ORR service pillar for this client (string)
- "roadmap_summary": A 2-3 sentence personalized engagement roadmap (string)
- "immediate_actions": Array of 2-3 recommended first steps (array of strings)
- "ai_notes": Internal notes for the ORR admin team about this client (string)

Return ONLY valid JSON, no markdown formatting."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini onboarding analysis failed: {e}")
        return _fallback_onboarding_analysis(orr_pillars)


def chat(
    message: str,
    conversation_history: Optional[List[Dict]] = None,
    user_context: str = "",
) -> str:
    """
    General-purpose AI chat for the ORR assistant.

    conversation_history should be a list of dicts with 'role' and 'content' keys.
    Returns the AI response as a string.
    """
    client = _get_client()
    if not client:
        return (
            "I'm currently unavailable. Please try again shortly, or reach out "
            "to the ORR Solutions team directly via the Support page."
        )

    system_prompt = ORR_SYSTEM_CONTEXT
    if user_context:
        system_prompt += f"\n\nCurrent user context:\n{user_context}"

    # Build conversation contents for Gemini
    contents = []
    if conversation_history:
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

    # Add the current message
    contents.append({"role": "user", "parts": [{"text": message}]})

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.7,
                "max_output_tokens": 1024,
            },
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini chat failed: {e}")
        return (
            "I apologise — I'm experiencing a temporary issue. Please try again "
            "in a moment, or contact the ORR team directly for immediate assistance."
        )


def generate_dashboard_insights(
    total_clients: int,
    active_clients: int,
    total_tickets: int,
    open_tickets: int,
    total_meetings: int,
    upcoming_meetings: int,
    recent_signups: int = 0,
    resolution_rate: float = 0.0,
) -> Dict:
    """
    Generate AI insights for the admin dashboard.

    Returns dict with keys: summary, highlights, alerts, recommendations.
    """
    client = _get_client()
    if not client:
        return _fallback_dashboard_insights()

    prompt = f"""{ORR_SYSTEM_CONTEXT}

You are providing a weekly intelligence briefing for the ORR Solutions admin team. Analyze the following platform metrics.

Total Clients: {total_clients}
Active Clients (30 days): {active_clients}
Recent Signups (7 days): {recent_signups}
Total Tickets: {total_tickets}
Open Tickets: {open_tickets}
Ticket Resolution Rate: {resolution_rate:.1f}%
Total Meetings: {total_meetings}
Upcoming Meetings: {upcoming_meetings}

Return a JSON object with these exact keys:
- "summary": A 2-3 sentence executive summary of platform health (string)
- "highlights": Array of 2-3 positive metrics or trends (array of strings)
- "alerts": Array of 0-2 items that need attention (array of strings)
- "recommendations": Array of 2-3 strategic suggestions (array of strings)

Return ONLY valid JSON, no markdown formatting."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini dashboard insights failed: {e}")
        return _fallback_dashboard_insights()


# ---------------------------------------------------------------------------
# Fallback Responses (used when Gemini is unavailable)
# ---------------------------------------------------------------------------


def _fallback_ticket_reply(client_name: str = "") -> str:
    name = client_name or "there"
    return (
        f"Thank you for reaching out, {name}. We have received your message and "
        f"your assigned administrator has been notified. We will follow up with "
        f"you as soon as practicable via the client portal.\n\n— ORR Solutions Team"
    )


def _fallback_meeting_prep(meeting_type: str, client_name: str) -> Dict:
    return {
        "summary": f"Upcoming {meeting_type} meeting with {client_name}. Review the client's current stage and recent interactions before the session.",
        "talking_points": [
            "Review client's current engagement status",
            "Discuss progress since last interaction",
            "Address any outstanding concerns or questions",
            "Outline next steps and deliverables",
        ],
        "suggested_questions": [
            "What has changed since our last meeting?",
            "Are there any new challenges you're facing?",
            "What are your priorities for the coming period?",
        ],
        "recommendations": [
            "Review latest client documents and notes",
            "Check for any pending tickets or requests",
        ],
    }


def _fallback_client_insights() -> Dict:
    return {
        "health_score": 50,
        "insights": ["Insufficient data for detailed analysis. Continue engagement to build a clearer picture."],
        "recommendations": ["Schedule a follow-up meeting to better understand client needs."],
        "risk_flags": [],
    }


def _fallback_onboarding_analysis(orr_pillars: list) -> Dict:
    pillar = orr_pillars[0] if orr_pillars else "Strategic Advisory & Compliance"
    return {
        "recommended_pillar": pillar,
        "roadmap_summary": "Based on your onboarding responses, we recommend starting with a Discovery consultation to align on your specific needs and goals.",
        "immediate_actions": [
            "Schedule your first Discovery meeting",
            "Complete your client profile with additional business details",
        ],
        "ai_notes": "AI analysis unavailable — manual review recommended.",
    }


def _fallback_dashboard_insights() -> Dict:
    return {
        "summary": "AI insights are temporarily unavailable. Please review the metrics above for current platform status.",
        "highlights": [],
        "alerts": [],
        "recommendations": ["Review open tickets and ensure timely responses."],
    }
