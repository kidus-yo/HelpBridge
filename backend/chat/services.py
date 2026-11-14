import logging
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from .models import ChatSession, Message
from ai_engine.services.answer_service import AnswerGenerationService

logger = logging.getLogger(__name__)

_answer_service = AnswerGenerationService()

def create_chat_session(institution_id='inst-default', course_id='course-va-101', channel='web', preferred_language='en', user=None):
    """
    Creates a new chat session and initializes default accessibility preferences.
    """
    session = ChatSession.objects.create(
        user=user,
        institution_id=institution_id or 'inst-default',
        course_id=course_id or 'course-va-101',
        channel=channel,
        preferred_language=preferred_language,
        status='active'
    )
    from accessibility.models import AccessibilityPreference
    AccessibilityPreference.objects.create(
        session=session,
        user=user,
        preferred_language=preferred_language
    )
    return session

def process_learner_message(session_id, content: str, language: str = None):
    """
    Core conversation workflow:
    1. Validates session status.
    2. Stores learner message.
    3. Calls AI answer generation (Samuel's AnswerGenerationService).
    4. Stores assistant response and citations.
    5. Returns structured response.
    """
    try:
        session = ChatSession.objects.get(id=session_id)
    except (ChatSession.DoesNotExist, ValueError):
        raise NotFound(detail=f"ChatSession with ID {session_id} not found.")

    if session.status != 'active':
        raise DRFValidationError(detail="This chat session is closed.")

    msg_lang = language or session.preferred_language or 'en'
    content = content.strip()
    if not content:
        raise DRFValidationError(detail="Message content cannot be empty.")
    if len(content) > 4000:
        raise DRFValidationError(detail="Message exceeds 4000 character limit.")

    # 1. Store learner message
    learner_msg = Message.objects.create(
        session=session,
        sender_type='learner',
        content=content,
        language=msg_lang
    )

    # 2. Call AnswerGenerationService with fallback safety
    course_id = str(session.course_id) if session.course_id else 'course-va-101'
    try:
        ai_result = _answer_service.answer_question(
            question=content,
            course_id=course_id,
            language=msg_lang
        )
    except Exception as exc:
        logger.error(f"AI Engine failure for session {session_id}: {exc}", exc_info=True)
        fallback_msg = (
            "ይቅርታ፣ አሁን መልስ መስጠት አልቻልኩም። እባክዎ ትንሽ ቆይተው እንደገና ይሞክሩ ወይም የሰው ድጋፍ ሰጪ ይጠይቁ።"
            if msg_lang == 'am'
            else "I'm sorry, I encountered a temporary issue generating a response. Please try again or request human support."
        )
        ai_result = {
            "answer": fallback_msg,
            "language": msg_lang,
            "grounded": False,
            "fallback_used": True,
            "citations": []
        }

    # 3. Store assistant message
    assistant_msg = Message.objects.create(
        session=session,
        sender_type='assistant',
        content=ai_result.get("answer", ""),
        language=ai_result.get("language", msg_lang),
        metadata={
            "citations": ai_result.get("citations", []),
            "grounded": ai_result.get("grounded", False),
            "fallback_used": ai_result.get("fallback_used", False)
        }
    )

    return {
        "learner_message": {
            "id": str(learner_msg.id),
            "content": learner_msg.content,
            "sender_type": learner_msg.sender_type,
            "created_at": learner_msg.created_at.isoformat()
        },
        "assistant_message": {
            "id": str(assistant_msg.id),
            "content": assistant_msg.content,
            "sender_type": assistant_msg.sender_type,
            "language": assistant_msg.language,
            "created_at": assistant_msg.created_at.isoformat()
        },
        "citations": ai_result.get("citations", []),
        "grounded": ai_result.get("grounded", False),
        "fallback_used": ai_result.get("fallback_used", False)
    }
