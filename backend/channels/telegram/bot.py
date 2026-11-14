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
                "• ከሰው አስተማሪ ጋር ለመገናኘት 'ከሰው ጋር ተነጋገር' ማለት ይችላሉ።"
                if lang == 'am' else
                "📖 **Digital Bridge Assistant Help**\n\n"
                "• Text any course question; the assistant answers using grounded course evidence.\n"
                "• Type `/language` anytime to change language.\n"
                "• If an answer cannot be found, you can request human assistance."
            )
            self.client.send_message(chat_id=chat_id, text=help_text)
            return {"ok": True, "action": "help"}

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
