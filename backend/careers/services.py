"""
Services for Grounded Job Q&A and Outbound Alert Dispatching.
"""

import logging
from typing import Dict, Any, List
from django.core.exceptions import ValidationError
from careers.models import JobListing, JobAlertSubscription

logger = logging.getLogger(__name__)


class JobQAService:
    """
    Answers questions regarding a specific job listing strictly using verified, published fields.
    Refuses missing information honestly without fabricating hiring details.
    """

    @classmethod
    def answer_question(cls, job: JobListing, question: str, language: str = 'en') -> Dict[str, Any]:
        if not question or not question.strip():
            raise ValidationError({'question': 'Question cannot be empty.'})

        q_lower = question.lower().strip()
        job_data = {
            'title': job.title,
            'organization': job.organization,
            'location': job.location,
            'employment_type': job.get_employment_type_display(),
            'remote_policy': job.get_remote_policy_display(),
            'description': job.description,
            'salary': job.salary_info,
            'deadline': str(job.deadline) if job.deadline else None,
            'skills': job.required_skills,
            'application_url': job.application_url,
            'contact_instructions': job.contact_instructions,
        }

        # Check specific field queries
        if any(term in q_lower for term in ['salary', 'pay', 'compensation', 'wage', 'stipend', 'rate']):
            if job.salary_info:
                answer = f"The published salary for {job.title} at {job.organization} is {job.salary_info}."
                grounded = True
                field = 'salary_info'
            else:
                answer = (
                    f"Salary information is not provided in the published details for {job.title} at {job.organization}. "
                    "You may contact the employer directly or request interview accommodation."
                )
                grounded = False
                field = None

        elif any(term in q_lower for term in ['deadline', 'closing date', 'due date', 'last date', 'apply by']):
            if job.deadline:
                answer = f"The application deadline for {job.title} is {job.deadline.strftime('%B %d, %Y')}."
                grounded = True
                field = 'deadline'
            else:
                answer = f"No specific application deadline is provided in the published listing for {job.title}."
                grounded = False
                field = None

        elif any(term in q_lower for term in ['remote', 'work from home', 'hybrid', 'on-site', 'onsite', 'location', 'where']):
            answer = (
                f"{job.title} at {job.organization} is located in {job.location}. "
                f"Work arrangement: {job.get_remote_policy_display()} ({job.get_employment_type_display()})."
            )
            grounded = True
            field = 'location'

        elif any(term in q_lower for term in ['skill', 'requirement', 'qualif', 'prereq', 'technolog', 'stack']):
            if job.required_skills:
                skills_str = ', '.join(job.required_skills) if isinstance(job.required_skills, list) else str(job.required_skills)
                answer = f"Required skills and qualifications for {job.title}: {skills_str}."
                grounded = True
                field = 'required_skills'
            else:
                answer = f"Detailed skill prerequisites are not listed separately; please check the job description: {job.description[:300]}..."
                grounded = True
                field = 'description'

        elif any(term in q_lower for term in ['how to apply', 'apply', 'contact', 'link', 'submit']):
            how = job.application_url or job.contact_instructions or "Check with the employer."
            answer = f"Application instructions for {job.title}: {how}"
            grounded = True
            field = 'application_url'

        else:
            # Fallback to description summary
            answer = (
                f"About {job.title} at {job.organization}: {job.description[:400]}... "
                f"Location: {job.location} ({job.get_remote_policy_display()})."
            )
            grounded = True
            field = 'description'

        return {
            "job_id": str(job.id),
            "job_title": job.title,
            "organization": job.organization,
            "question": question,
            "answer": answer,
            "grounded": grounded,
            "field_referenced": field,
            "language": language,
            "source": f"JobListing:{job.id}"
        }


class JobAlertService:
    """
    Matches newly published job listings with active learner subscriptions
    and dispatches outbound alerts via Samuel's shared delivery adapter.
    """

    @classmethod
    def dispatch_alerts_for_job(cls, job: JobListing) -> int:
        if job.status != 'published':
            logger.info("Skipping job alert dispatch: job is not published.")
            return 0

        # Lazy import to avoid circular dependencies
        from channels.notifications.delivery import send_notification

        active_subs = JobAlertSubscription.objects.filter(is_active=True)
        dispatched_count = 0

        job_search_text = f"{job.title} {job.organization} {job.description} {' '.join(job.required_skills) if isinstance(job.required_skills, list) else ''}".lower()

        for sub in active_subs:
            # Check location match if specified
            if sub.location_preference and sub.location_preference.lower() not in job.location.lower():
                continue

            # Check keywords match if specified
            if sub.keywords:
                matched = any(kw.lower() in job_search_text for kw in sub.keywords if kw)
                if not matched:
                    continue

            # Format message based on channel
            if sub.channel == 'sms':
                # Compact 160-char SMS
                apply_link = job.application_url or 'HelpBridge'
                msg = f"Job: {job.title[:30]} at {job.organization[:20]}. Loc: {job.location[:15]}. Apply: {apply_link[:40]}. Stop: reply STOP"[:160]
                title = None
            else:
                # Telegram
                title = f"New Job: {job.title}"
                msg = (
                    f"🏢 **Organization:** {job.organization}\n"
                    f"📍 **Location:** {job.location} ({job.get_remote_policy_display()})\n"
                    f"💼 **Type:** {job.get_employment_type_display()}\n"
                    f"🔗 **Apply:** {job.application_url or job.contact_instructions or 'See portal'}"
                )

            try:
                send_notification(
                    recipient=sub.contact_identity,
                    message=msg,
                    channel=sub.channel,
                    title=title
                )
                dispatched_count += 1
            except Exception as e:
                logger.error(f"Failed to dispatch alert to {sub.contact_identity} via {sub.channel}: {e}")

        logger.info(f"Dispatched {dispatched_count} alerts for job {job.id}.")
        return dispatched_count
