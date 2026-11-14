"""
SMS Channel Adapter for Digital Bridge Assistant.
Fulfills Hackathon Track 3 requirement:
'Build one HTTP endpoint, POST /sms/inbound { from, text }, that returns the reply
 as plain text of at most 160 characters, and document how a gateway would call it.'
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from django.conf import settings
from channels.models import ChannelIdentity, MessageDelivery
from channels.sms.normalizer import normalize_ethiopian_phone
from common.contracts import MockChatService
from ai_engine.services.answer_service import generate_answer
from ai_engine.services.prompt_templates import format_citations_sms

logger = logging.getLogger(__name__)


class SMSAdapter:
    """Manages low-bandwidth SMS inbound routing and outbound notifications."""

    MAX_SMS_LENGTH = 160

    @classmethod
    def process_inbound(cls, from_phone: str, text: str) -> str:
        """
        Process incoming SMS message and return concise text reply <= 160 characters.
        """
        raw_text = (text or '').strip()
        if not raw_text:
            return "እባክዎ ጥያቄዎን ይላኩ። (Please text your course question.)"[:cls.MAX_SMS_LENGTH]

        # 1. Normalize phone
        try:
            phone = normalize_ethiopian_phone(from_phone)
        except ValueError as err:
            logger.warning("Rejected SMS from invalid phone: %s (%s)", from_phone, err)
            return "Invalid Ethiopian phone number. Use 09... or 07... format."[:cls.MAX_SMS_LENGTH]

        # 2. Get or create ChannelIdentity
        identity, created = ChannelIdentity.objects.get_or_create(
            channel='sms',
            external_id=phone,
            defaults={
                'phone_number': phone,
                'preferred_language': getattr(settings, 'DEFAULT_LANGUAGE', 'am'),
                'is_active': True
            }
        )

        # 3. Check for language switch command
        text_upper = raw_text.upper()
        if text_upper in ('LANG AM', 'AMHARIC', 'አማርኛ'):
            identity.preferred_language = 'am'
            identity.save(update_fields=['preferred_language', 'updated_at'])
            return "ቋንቋዎ ወደ አማርኛ ተቀይሯል። ጥያቄዎን አሁን መላክ ይችላሉ።"[:cls.MAX_SMS_LENGTH]
        elif text_upper in ('LANG EN', 'ENGLISH'):
            identity.preferred_language = 'en'
            identity.save(update_fields=['preferred_language', 'updated_at'])
            return "Language switched to English. You can now text your question."[:cls.MAX_SMS_LENGTH]

        # 4. Attach chat session
        if not identity.session_id:
            session = MockChatService.get_or_create_session_for_channel(
                channel='sms',
                external_id=phone,
                preferred_language=identity.preferred_language
            )
            identity.session_id = session.get('id')
            identity.save(update_fields=['session_id', 'updated_at'])

        # Store learner message in chat history
        MockChatService.append_message(
            session_id=identity.session_id,
            sender_type='learner',
            content=raw_text,
            language=identity.preferred_language
        )

        # 5. Generate grounded answer
        ai_result = generate_answer(
            question=raw_text,
            language=identity.preferred_language
        )

        answer_body = ai_result.get('answer', '').strip()
        citations = ai_result.get('citations', [])
        cite_str = format_citations_sms(citations, language=identity.preferred_language)

        # 6. Format and clamp reply to <= 160 characters
        allowed_body_len = cls.MAX_SMS_LENGTH - len(cite_str)
        if len(answer_body) > allowed_body_len:
            # Cut at space boundary
            truncated = answer_body[:allowed_body_len - 3]
            last_space = truncated.rfind(' ')
            if last_space > 40:
                truncated = truncated[:last_space]
            answer_body = f"{truncated}..."

        final_sms = f"{answer_body}{cite_str}".strip()[:cls.MAX_SMS_LENGTH]

        # Store assistant response in chat history
        MockChatService.append_message(
            session_id=identity.session_id,
            sender_type='assistant',
            content=final_sms,
            language=identity.preferred_language,
            metadata={'grounded': ai_result.get('grounded'), 'citations': citations}
        )

        return final_sms

    @classmethod
    def send_outbound(cls, to_phone: str, text: str) -> Dict[str, Any]:
        """
        Send outbound SMS message (used by Yensew for career alerts or human replies).
        """
        try:
            phone = normalize_ethiopian_phone(to_phone)
        except ValueError as err:
            return {"status": "failed", "error": str(err)}

        clamped_text = text[:cls.MAX_SMS_LENGTH]
        delivery = MessageDelivery.objects.create(
            channel='sms',
            recipient=phone,
            content=clamped_text,
            status='delivered',  # Simulated delivery in hackathon environment
            delivered_at=datetime.now(timezone.utc)
        )

        return {
            "delivery_id": str(delivery.id),
            "channel": "sms",
            "recipient": phone,
            "status": delivery.status,
            "content": clamped_text,
            "delivered_at": delivery.delivered_at.isoformat()
        }
