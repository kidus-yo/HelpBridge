"""
Business logic and workflow orchestration for Support & Human Escalation.
"""

import uuid
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from django.core.exceptions import PermissionDenied, ValidationError
from support.models import SupportRequest, SupportMessage


class EscalationService:

    @classmethod
    def create_support_request(
        cls,
        subject: str,
        description: str,
        category: str = 'course',
        priority: str = 'normal',
        preferred_assistance_mode: str = 'chat',
        learner=None,
        guest_token: Optional[str] = None,
        institution_id: Optional[str] = None,
        chat_session_id: Optional[str] = None,
        learner_consent_chat_history: bool = False,
        language: str = 'en'
    ) -> SupportRequest:
        """
        Creates a new support request with explicit consent tracking.
        """
        if not subject or not subject.strip():
            raise ValidationError({'subject': 'Subject cannot be empty.'})
        if not description or not description.strip():
            raise ValidationError({'description': 'Description cannot be empty.'})

        # If guest learner, ensure a secure guest token is provided or generated
        final_guest_token = guest_token
        if not learner and not final_guest_token:
            final_guest_token = secrets.token_urlsafe(32)

        ticket = SupportRequest.objects.create(
            learner=learner if (learner and learner.is_authenticated) else None,
            guest_token=final_guest_token or '',
            institution_id=institution_id,
            chat_session_id=chat_session_id,
            learner_consent_chat_history=bool(learner_consent_chat_history),
            category=category,
            subject=subject.strip(),
            description=description.strip(),
            priority=priority,
            preferred_assistance_mode=preferred_assistance_mode,
            language=language,
            status='open'
        )

        # Initial system message
        consent_text = (
            "Chat history shared with agent."
            if ticket.learner_consent_chat_history
            else "Chat history kept private by learner choice."
        )
        SupportMessage.objects.create(
            support_request=ticket,
            sender_type='system',
            content=f"Support ticket created. Status: Open. {consent_text}"
        )

        return ticket

    @classmethod
    def post_message(
        cls,
        ticket: SupportRequest,
        sender_type: str,
        content: str,
        sender=None,
        is_snapshot: bool = False,
        snapshot_data: str = ''
    ) -> SupportMessage:
        """
        Appends a message to the support thread and updates ticket status accordingly.
        """
        if not content or not content.strip():
            raise ValidationError({'content': 'Message content cannot be empty.'})

        msg = SupportMessage.objects.create(
            support_request=ticket,
            sender_type=sender_type,
            sender=sender if (sender and sender.is_authenticated) else None,
            content=content.strip(),
            is_snapshot=is_snapshot,
            snapshot_data=snapshot_data
        )

        # If an agent sends a message and ticket was open or assigned, progress to in_progress
        if sender_type == 'agent' and ticket.status in ['open', 'assigned']:
            ticket.status = 'in_progress'
            ticket.save(update_fields=['status', 'updated_at'])

        return msg

    @classmethod
    def update_status(
        cls,
        ticket: SupportRequest,
        new_status: str,
        agent=None
    ) -> SupportRequest:
        """
        Updates the status of a support ticket and handles agent assignment.
        """
        valid_statuses = [choice[0] for choice in SupportRequest.STATUS_CHOICES]
        if new_status not in valid_statuses:
            raise ValidationError({'status': f"Invalid status '{new_status}'. Allowed: {valid_statuses}"})

        ticket.status = new_status
        if agent and agent.is_authenticated:
            ticket.assigned_agent = agent
            if ticket.status == 'open':
                ticket.status = 'assigned'

        ticket.save()

        SupportMessage.objects.create(
            support_request=ticket,
            sender_type='system',
            content=f"Ticket status changed to '{ticket.status}'" + (f" by {agent.username}" if agent else "")
        )

        return ticket

    @classmethod
    def start_screen_share(cls, ticket: SupportRequest) -> Dict[str, Any]:
        """
        Initiates a learner-controlled screen sharing session.
        Only the learner can initiate this.
        """
        token = secrets.token_urlsafe(24)
        ticket.screen_share_active = True
        ticket.screen_share_token = token
        ticket.screen_share_started_at = datetime.now(timezone.utc)
        ticket.screen_share_stopped_at = None
        ticket.save(update_fields=['screen_share_active', 'screen_share_token', 'screen_share_started_at', 'screen_share_stopped_at'])

        SupportMessage.objects.create(
            support_request=ticket,
            sender_type='system',
            content="Learner started screen sharing session. Screen is now visible to the support agent."
        )

        return {
            "screen_share_active": True,
            "session_token": token,
            "started_at": ticket.screen_share_started_at.isoformat(),
            "status_announcement": "Screen sharing is active. Agent can see your screen."
        }

    @classmethod
    def stop_screen_share(cls, ticket: SupportRequest) -> Dict[str, Any]:
        """
        Stops the screen sharing session immediately.
        Learner maintains 100% control over termination.
        """
        ticket.screen_share_active = False
        ticket.screen_share_token = ''
        ticket.screen_share_stopped_at = datetime.now(timezone.utc)
        ticket.save(update_fields=['screen_share_active', 'screen_share_token', 'screen_share_stopped_at'])

        SupportMessage.objects.create(
            support_request=ticket,
            sender_type='system',
            content="Learner stopped screen sharing session. Screen is no longer visible."
        )

        return {
            "screen_share_active": False,
            "stopped_at": ticket.screen_share_stopped_at.isoformat(),
            "status_announcement": "Screen sharing stopped. Agent can no longer see your screen."
        }

    @classmethod
    def send_screen_snapshot(cls, ticket: SupportRequest, snapshot_data: str, description: str = '') -> SupportMessage:
        """
        Low-bandwidth fallback: Sends a single static DOM or image snapshot instead of video streaming.
        """
        return cls.post_message(
            ticket=ticket,
            sender_type='learner',
            content=description or "Shared screen snapshot (low-bandwidth mode).",
            is_snapshot=True,
            snapshot_data=snapshot_data
        )
