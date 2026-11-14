"""
Multilingual Prompt Templates and Citation Formatters for Digital Bridge Assistant.
Supports English ('en') and Amharic ('am') with Ethiopic script.
"""

from typing import List, Dict, Any

REFUSALS = {
    'en': (
        "I could not find this information in the course material. "
        "Would you like to speak to a human instructor or support agent?"
    ),
    'am': (
        "ይህንን መረጃ በኮርሱ ይዘት ውስጥ ማግኘት አልቻልኩም። "
        "ከሰው አስተማሪ ወይም የድጋፍ ባለሙያ ጋር መነጋገር ይፈልጋሉ?"
    )
}

HUMAN_HELP_PROMPT = {
    'en': "\n\n💡 Need live help? Click 'Talk to a human' to connect with an instructor.",
    'am': "\n\n💡 የቀጥታ ድጋፍ ይፈልጋሉ? ከአስተማሪ ጋር ለመገናኘት 'ከሰው ጋር ተነጋገር' የሚለውን ይጫኑ።"
}


def format_citations_markdown(citations: List[Dict[str, Any]], language: str = 'en') -> str:
    """Format citations into a readable markdown footnote for Telegram or widget."""
    if not citations:
        return ""

    lang = 'am' if language == 'am' else 'en'
    header = "\n\n📚 **ዋቢ ምንጮች (Sources):**" if lang == 'am' else "\n\n📚 **Course Sources:**"
    lines = [header]

    for i, c in enumerate(citations, 1):
        sec = c.get('section', 'Section')
        doc = c.get('document_title', 'Course Document')
        url = c.get('url', '')
        page = c.get('page')
        page_str = f", ገጽ {page}" if lang == 'am' and page else (f", p. {page}" if page else "")

        if url:
            lines.append(f"{i}. [{sec}]({url}) — {doc}{page_str}")
        else:
            lines.append(f"{i}. {sec} — {doc}{page_str}")

    return "\n".join(lines)


def format_citations_sms(citations: List[Dict[str, Any]], language: str = 'en') -> str:
    """Format concise citation for 160-char SMS replies."""
    if not citations:
        return ""
    top = citations[0]
    sec = top.get('section', '')
    if sec:
        return f" [Ref: {sec[:25]}]"
    return ""
