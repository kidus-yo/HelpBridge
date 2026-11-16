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
    Supports English and Amharic queries.
    Refuses missing information honestly without fabricating hiring details.
    """

    @classmethod
    def answer_question(cls, job: JobListing, question: str, language: str = 'en') -> Dict[str, Any]:
        if not question or not question.strip():
            raise ValidationError({'question': 'Question cannot be empty.'})

        q_lower = question.lower().strip()
        is_amharic = (
            language == 'am' or
            any('\u1200' <= char <= '\u137f' for char in question)
        )

        # 1. Salary Queries
        salary_terms_en = ['salary', 'pay', 'compensation', 'wage', 'stipend', 'rate']
        salary_terms_am = ['ደመወዝ', 'ደሞዝ', 'ክፍያ', 'ስንት ይከፍላል', 'አበል']
        if any(term in q_lower for term in salary_terms_en) or any(term in question for term in salary_terms_am):
            if job.salary_info:
                if is_amharic:
                    answer = f"ለ{job.title} በ{job.organization} የተገለጸው ደመወዝ {job.salary_info} ነው።"
                else:
                    answer = f"The published salary for {job.title} at {job.organization} is {job.salary_info}."
                grounded = True
                field = 'salary_info'
            else:
                if is_amharic:
                    answer = (
                        f"ለ{job.title} በ{job.organization} የወጣው የሥራ ማስታወቂያ ላይ ስለ ደመወዝ የተገለጸ መረጃ የለም። "
                        "አሰሪውን በቀጥታ መጠየቅ ወይም የቃለ-መጠይቅ ማመቻቻ ጥያቄ ማቅረብ ይችላሉ።"
                    )
                else:
                    answer = (
                        f"Salary information is not provided in the published details for {job.title} at {job.organization}. "
                        "You may contact the employer directly or request interview accommodation."
                    )
                grounded = False
                field = None

        # 2. Deadline Queries
        elif any(term in q_lower for term in ['deadline', 'closing date', 'due date', 'last date', 'apply by']) or any(term in question for term in ['የመጨረሻ ቀን', 'ማብቂያ', 'መቼ ያበቃል']):
            if job.deadline:
                if is_amharic:
                    answer = f"ለ{job.title} የማመልከቻው የመጨረሻ ቀን {job.deadline.strftime('%B %d, %Y')} ነው።"
                else:
                    answer = f"The application deadline for {job.title} is {job.deadline.strftime('%B %d, %Y')}."
                grounded = True
                field = 'deadline'
            else:
                if is_amharic:
                    answer = f"ለ{job.title} የተለየ የማመልከቻ ማብቂያ ቀን በማስታወቂያው ላይ አልተጠቀሰም።"
                else:
                    answer = f"No specific application deadline is provided in the published listing for {job.title}."
                grounded = False
                field = None

        # 3. Location / Remote Queries
        elif any(term in q_lower for term in ['remote', 'work from home', 'hybrid', 'on-site', 'onsite', 'location', 'where']) or any(term in question for term in ['ቦታ', 'የት', 'ከቤት', 'በሩቅ', 'አድራሻ']):
            if is_amharic:
                answer = (
                    f"{job.title} በ{job.organization} የሚገኝበት ቦታ፡ {job.location}። "
                    f"የሥራ ሁኔታ፡ {job.get_remote_policy_display()} ({job.get_employment_type_display()})።"
                )
            else:
                answer = (
                    f"{job.title} at {job.organization} is located in {job.location}. "
                    f"Work arrangement: {job.get_remote_policy_display()} ({job.get_employment_type_display()})."
                )
            grounded = True
            field = 'location'

        # 4. Skills & Requirements
        elif any(term in q_lower for term in ['skill', 'requirement', 'qualif', 'prereq', 'technolog', 'stack']) or any(term in question for term in ['ችሎታ', 'መስፈርት', 'እውቀት', 'ምን ያስፈልጋል']):
            if job.required_skills:
                skills_str = ', '.join(job.required_skills) if isinstance(job.required_skills, list) else str(job.required_skills)
                if is_amharic:
                    answer = f"ለ{job.title} የሚያስፈልጉ ዋና ችሎታዎችና መስፈርቶች፡ {skills_str}።"
                else:
                    answer = f"Required skills and qualifications for {job.title}: {skills_str}."
                grounded = True
                field = 'required_skills'
            else:
                if is_amharic:
                    answer = f"ዝርዝር መስፈርቶች ለብቻቸው አልተዘረዘሩም፤ እባክዎ ሙሉ የሥራውን መግለጫ ይመልከቱ፡ {job.description[:300]}..."
                else:
                    answer = f"Detailed skill prerequisites are not listed separately; please check the job description: {job.description[:300]}..."
                grounded = True
                field = 'description'

        # 5. How to Apply
        elif any(term in q_lower for term in ['how to apply', 'apply', 'contact', 'link', 'submit']) or any(term in question for term in ['እንዴት ማመልከት', 'ማመልከቻ', 'ማመልከት']):
            how = job.application_url or job.contact_instructions or "Check with the employer."
            if is_amharic:
                answer = f"ለ{job.title} የማመልከቻ መንገድ፡ {how}።"
            else:
                answer = f"Application instructions for {job.title}: {how}"
            grounded = True
            field = 'application_url'

        # 6. General Overview Fallback
        else:
            if is_amharic:
                answer = (
                    f"ስለ {job.title} በ{job.organization}፡ {job.description[:300]}... "
                    f"ቦታ፡ {job.location} ({job.get_remote_policy_display()})።"
                )
            else:
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
            "language": 'am' if is_amharic else 'en',
            "source": f"JobListing:{job.id}"
        }


class JobListingSimpleModeService:
    """
    Cognitive Accessibility & Plain Language (Simple Mode).
    De-jargonizes corporate job descriptions into clear, digestible, plain-language sections.
    """

    @classmethod
    def simplify(cls, job: JobListing, language: str = 'en') -> Dict[str, Any]:
        is_am = (language == 'am')

        # Extract essential skills as plain bullet points
        skills = job.required_skills if isinstance(job.required_skills, list) else [str(job.required_skills)]

        if is_am:
            return {
                "job_id": str(job.id),
                "title": job.title,
                "organization": job.organization,
                "language": "am",
                "plain_summary": f"ይህ ሥራ በ{job.organization} ድርጅት ውስጥ የሚሰራ የ{job.title} ክፍት የሥራ ቦታ ነው።",
                "what_you_will_do": [
                    f"በ{job.organization} ውስጥ እንደ {job.title} ሆነው ይሰራሉ",
                    f"የሥራው ቦታ፡ {job.location} ({job.get_remote_policy_display()})",
                    f"የሥራው ዓይነት፡ {job.get_employment_type_display()}"
                ],
                "what_you_need": skills or ["መሰረታዊ የቴክኖሎጂ እውቀት"],
                "pay_and_deadline": {
                    "salary": job.salary_info or "በማስታወቂያው ላይ አልተጠቀሰም",
                    "deadline": job.deadline.strftime('%B %d, %Y') if job.deadline else "ያልተወሰነ"
                },
                "how_to_apply": job.application_url or job.contact_instructions or "በቀጥታ አሰሪውን ያነጋግሩ",
                "interview_accommodations_note": "ማስታወሻ፡ በቃለ-መጠይቅ ወቅት ተጨማሪ ጊዜ ወይም የቴክኖሎጂ ማመቻቻ መጠየቅ ይችላሉ።"
            }
        else:
            return {
                "job_id": str(job.id),
                "title": job.title,
                "organization": job.organization,
                "language": "en",
                "plain_summary": f"In simple terms, this is a {job.get_employment_type_display()} role as {job.title} at {job.organization}.",
                "what_you_will_do": [
                    f"Work as {job.title} at {job.organization}",
                    f"Location: {job.location} ({job.get_remote_policy_display()})",
                    f"Commitment: {job.get_employment_type_display()}"
                ],
                "what_you_need": skills or ["Basic foundational skills"],
                "pay_and_deadline": {
                    "salary": job.salary_info or "Not stated in listing",
                    "deadline": job.deadline.strftime('%B %d, %Y') if job.deadline else "Open until filled"
                },
                "how_to_apply": job.application_url or job.contact_instructions or "Contact employer directly",
                "interview_accommodations_note": "Accessibility Guarantee: You have the right to request interview accommodations (such as screen reader support or extra time) using the accommodation form."
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
                result = send_notification(
                    recipient=sub.contact_identity,
                    message=msg,
                    channel=sub.channel,
                    title=title
                )
                if result.get("status") in {"pending", "sent", "delivered"}:
                    dispatched_count += 1
                else:
                    logger.warning(
                        "Job alert delivery failed for subscription %s (status=%s).",
                        sub.id,
                        result.get("status", "unknown"),
                    )
            except Exception:
                logger.exception(
                    "Could not dispatch job alert for subscription %s.",
                    sub.id,
                )

        logger.info(f"Dispatched {dispatched_count} alerts for job {job.id}.")
        return dispatched_count
