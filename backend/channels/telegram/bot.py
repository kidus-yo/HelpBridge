"""
Telegram Bot Message Handler and Workflow Dispatcher.
"""

import logging
from typing import Dict, Any, Optional
from django.conf import settings
from channels.models import ChannelIdentity
from channels.telegram.client import TelegramClient
from common.contracts import MockChatService
from ai_engine.services.answer_service import generate_answer
from ai_engine.services.prompt_templates import format_citations_markdown

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    def __init__(self, client: Optional[TelegramClient] = None):
        self.client = client or TelegramClient()

    def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Entry point for incoming Telegram updates (Webhook or Polling)."""
        if "callback_query" in update:
            return self._handle_callback(update["callback_query"])
        elif "message" in update:
            return self._handle_message(update["message"])
        return {"ok": True, "ignored": True}

    def _get_language_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "🇪🇹 አማርኛ (Amharic)", "callback_data": "set_lang_am"},
                    {"text": "🇬🇧 English", "callback_data": "set_lang_en"}
                ]
            ]
        }

    def _handle_callback(self, cb: Dict[str, Any]) -> Dict[str, Any]:
        cb_id = cb.get("id")
        data = cb.get("data", "")
        from_user = cb.get("from", {})
        user_id = str(from_user.get("id"))
        chat_id = cb.get("message", {}).get("chat", {}).get("id")

        identity, _ = ChannelIdentity.objects.get_or_create(
            channel='telegram',
            external_id=user_id,
            defaults={
                'username': from_user.get('username'),
                'preferred_language': 'am',
                'is_active': True
            }
        )

        if data == "set_lang_am":
            identity.preferred_language = "am"
            identity.save(update_fields=['preferred_language', 'updated_at'])
            self.client.answer_callback_query(cb_id, text="ቋንቋዎ ወደ አማርኛ ተቀይሯል!")
            self.client.send_message(
                chat_id=chat_id,
                text="✅ **ቋንቋዎ በተሳካ ሁኔታ ወደ አማርኛ ተቀይሯል።**\n\nስለ ኮርሱ ማንኛውንም ጥያቄ እዚህ መላክ ይችላሉ።"
            )
        elif data == "set_lang_en":
            identity.preferred_language = "en"
            identity.save(update_fields=['preferred_language', 'updated_at'])
            self.client.answer_callback_query(cb_id, text="Language set to English!")
            self.client.send_message(
                chat_id=chat_id,
                text="✅ **Language successfully set to English.**\n\nYou can now ask any question about the course."
            )

        return {"ok": True, "callback_handled": data}

    def _handle_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        from_user = msg.get("from", {})
        user_id = str(from_user.get("id"))
        text = (msg.get("text") or "").strip()

        if not text or not chat_id:
            return {"ok": True}

        identity, created = ChannelIdentity.objects.get_or_create(
            channel='telegram',
            external_id=user_id,
            defaults={
                'username': from_user.get('username'),
                'preferred_language': getattr(settings, 'DEFAULT_LANGUAGE', 'am'),
                'is_active': True
            }
        )

        # Connect or create chat session
        if not identity.session_id:
            session = MockChatService.get_or_create_session_for_channel(
                channel='telegram',
                external_id=user_id,
                preferred_language=identity.preferred_language
            )
            identity.session_id = session.get('id')
            identity.save(update_fields=['session_id', 'updated_at'])

        lang = identity.preferred_language

        # Command /start
        if text.startswith("/start"):
            welcome_text = (
                "👋 **እንኳን ወደ ዲጂታል ብሪጅ ረዳት በደህና መጡ!**\n"
                "**Welcome to Digital Bridge Assistant!**\n\n"
                "ይህ ቦት ስለ ALX Savanna ኮርሶች እና ስለ ሥራ ዕድሎች ጥያቄዎችን ለመመለስ የተዘጋጀ ነው።\n"
                "This assistant helps you with course content, citations, and career access.\n\n"
                "👉 እባክዎ የሚመርጡትን ቋንቋ ይምረጡ / Please select your preferred language:"
            )
            self.client.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=self._get_language_keyboard()
            )
            return {"ok": True, "action": "start"}

        # Command /language
        if text.startswith("/language") or text.startswith("/lang"):
            prompt_text = (
                "ቋንቋዎን ይምረጡ / Select your preferred language:"
            )
            self.client.send_message(
                chat_id=chat_id,
                text=prompt_text,
                reply_markup=self._get_language_keyboard()
            )
            return {"ok": True, "action": "language_select"}

        # Command /help
        if text.startswith("/help"):
            help_text = (
                "📖 **የዲጂታል ብሪጅ ረዳት አጠቃቀም መመሪያ**\n\n"
                "• ጥያቄዎን በጽሑፍ ይላኩ፤ ረዳቱ ከትክክለኛ የኮርሱ ይዘት አመሳክሮ መልስ ይሰጣል።\n"
                "• ቋንቋ ለመቀየር `/language` ይላኩ።\n"
                "• ክፍት የሥራ ዕድሎችን ለማየት `/jobs` ይላኩ።\n"
                "• አዳዲስ የሥራ ማስታወቂያዎች በቴሌግራም እንዲደርስዎት `/subscribe` ይላኩ።\n"
                "• ከሰው አስተማሪ ጋር ለመገናኘት 'ከሰው ጋር ተነጋገር' ማለት ይችላሉ።"
                if lang == 'am' else
                "📖 **Digital Bridge Assistant Help**\n\n"
                "• Text any course question; the assistant answers using grounded course evidence.\n"
                "• Type `/language` anytime to change language.\n"
                "• Type `/jobs` to view latest accessible job opportunities.\n"
                "• Type `/subscribe` to receive real-time job alerts in Telegram.\n"
                "• If an answer cannot be found, you can request human assistance."
            )
            self.client.send_message(chat_id=chat_id, text=help_text)
            return {"ok": True, "action": "help"}

        # Command /jobs
        if text.startswith("/jobs") or text.startswith("/career"):
            from careers.models import JobListing
            jobs = JobListing.objects.filter(status='published')[:5]
            if not jobs.exists():
                msg = (
                    "በአሁኑ ሰዓት ክፍት የሥራ ማስታወቂያዎች የሉም። እባክዎ ትንሽ ቆይተው እንደገና ይመልከቱ።"
                    if lang == 'am' else
                    "No published job opportunities at the moment. Please check back soon."
                )
            else:
                if lang == 'am':
                    msg = "💼 **የቅርብ ጊዜ ክፍት የሥራ ዕድሎች (Latest Tech Jobs):**\n\n"
                    for idx, j in enumerate(jobs, 1):
                        msg += (
                            f"{idx}. **{j.title}**\n"
                            f"   🏢 ድርጅት: {j.organization}\n"
                            f"   📍 ቦታ: {j.location} ({j.get_remote_policy_display()})\n"
                            f"   💰 ደመወዝ: {j.salary_info or 'ያልተገለጸ'}\n"
                            f"   🔗 ማመልከቻ: {j.application_url or 'በፖርታሉ ይመልከቱ'}\n\n"
                        )
                    msg += "🔔 አዳዲስ የሥራ ማስታወቂያዎች ሲወጡ በቴሌግራም መልእክት እንዲደርስዎ `/subscribe` ብለው ይላኩ።"
                else:
                    msg = "💼 **Latest Accessible Job Opportunities:**\n\n"
                    for idx, j in enumerate(jobs, 1):
                        msg += (
                            f"{idx}. **{j.title}**\n"
                            f"   🏢 Org: {j.organization}\n"
                            f"   📍 Location: {j.location} ({j.get_remote_policy_display()})\n"
                            f"   💰 Pay: {j.salary_info or 'Not specified'}\n"
                            f"   🔗 Apply: {j.application_url or 'Check LMS portal'}\n\n"
                        )
                    msg += "🔔 Type `/subscribe` to receive alerts when new jobs are published."

            self.client.send_message(chat_id=chat_id, text=msg)
            return {"ok": True, "action": "jobs_list", "count": jobs.count()}

        # Command /subscribe or /jobalerts
        if text.startswith("/subscribe") or text.startswith("/jobalerts") or text.startswith("/alert"):
            from careers.models import JobAlertSubscription
            sub, created = JobAlertSubscription.objects.get_or_create(
                channel='telegram',
                contact_identity=str(chat_id),
                defaults={'is_active': True}
            )
            if not sub.is_active:
                sub.is_active = True
                sub.save(update_fields=['is_active', 'updated_at'])

            msg = (
                "✅ **የሥራ ማስታወቂያ ማሳወቂያ በተሳካ ሁኔታ ተመዝግቧል!**\n\n"
                "አዳዲስ የቴክኖሎጂ የሥራ ዕድሎች ሲወጡ ወዲያውኑ በዚህ የቴሌግራም ቻት ይደርስዎታል።\n"
                "ለማቆም በማንኛውም ሰዓት `/unsubscribe` መላክ ይችላሉ።"
                if lang == 'am' else
                "✅ **Job alerts successfully enabled!**\n\n"
                "You will receive immediate Telegram notifications whenever new tech jobs are published.\n"
                "Type `/unsubscribe` anytime to stop alerts."
            )
            self.client.send_message(chat_id=chat_id, text=msg)
            return {"ok": True, "action": "subscribe"}

        # Command /unsubscribe
        if text.startswith("/unsubscribe") or text.startswith("/stop"):
            from careers.models import JobAlertSubscription
            JobAlertSubscription.objects.filter(
                channel='telegram',
                contact_identity=str(chat_id)
            ).update(is_active=False)

            msg = (
                "❌ **የሥራ ማስታወቂያ ምዝገባዎ ተሰርዟል።**\n\nእንደገና ለመመዝገብ `/subscribe` ይላኩ።"
                if lang == 'am' else
                "❌ **Job alerts unsubscribed.**\n\nType `/subscribe` anytime to resume notifications."
            )
            self.client.send_message(chat_id=chat_id, text=msg)
            return {"ok": True, "action": "unsubscribe"}

        # Record learner message in central conversation lifecycle
        MockChatService.append_message(
            session_id=identity.session_id,
            sender_type='learner',
            content=text,
            language=lang
        )

        # Generate evidence-grounded answer
        ai_result = generate_answer(
            question=text,
            language=lang
        )

        reply_content = ai_result.get("answer", "")
        citations = ai_result.get("citations", [])
        if citations:
            reply_content += format_citations_markdown(citations, language=lang)

        # Record assistant reply
        MockChatService.append_message(
            session_id=identity.session_id,
            sender_type='assistant',
            content=reply_content,
            language=lang,
            metadata={'grounded': ai_result.get('grounded'), 'citations': citations}
        )

        self.client.send_message(chat_id=chat_id, text=reply_content)
        return {
            "ok": True,
            "action": "answer",
            "grounded": ai_result.get("grounded"),
            "citations_count": len(citations)
        }
