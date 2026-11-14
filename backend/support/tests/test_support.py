import pytest
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from support.models import SupportRequest, SupportMessage


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def learner_user():
    return User.objects.create_user(username='learner1', password='password123')


@pytest.fixture
def other_learner():
    return User.objects.create_user(username='learner2', password='password123')


@pytest.fixture
def support_agent():
    user = User.objects.create_user(username='agent_sara', password='password123')
    group, _ = Group.objects.get_or_create(name='SupportAgent')
    user.groups.add(group)
    return user


@pytest.fixture
def staff_user():
    return User.objects.create_superuser(username='admin_yensew', password='password123')


@pytest.mark.django_db
class TestSupportRequests:

    def test_learner_can_create_support_request_with_consent(self, api_client, learner_user):
        api_client.force_authenticate(user=learner_user)
        payload = {
            "subject": "Help with Python Loops",
            "description": "My while loop is not terminating on line 4.",
            "category": "course",
            "priority": "high",
            "preferred_assistance_mode": "chat",
            "learner_consent_chat_history": True,
            "language": "en"
        }
        response = api_client.post('/api/v1/support/requests/', payload, format='json')
        assert response.status_code == 201
        data = response.data
        assert data['subject'] == "Help with Python Loops"
        assert data['learner_consent_chat_history'] is True
        assert data['status'] == 'open'
        assert 'accessibility_meta' in data
        assert "Waiting for an agent" in data['accessibility_meta']['status_announcement']

    def test_learner_can_create_support_request_without_consent(self, api_client, learner_user):
        api_client.force_authenticate(user=learner_user)
        payload = {
            "subject": "Technical Glitch",
            "description": "Video won't play",
            "category": "technical",
            "learner_consent_chat_history": False
        }
        response = api_client.post('/api/v1/support/requests/', payload, format='json')
        assert response.status_code == 201
        assert response.data['learner_consent_chat_history'] is False

    def test_guest_learner_can_create_and_view_ticket_with_token(self, api_client):
        payload = {
            "subject": "Guest Access Issue",
            "description": "I cannot load the PDF in Savanna demo.",
            "category": "course"
        }
        create_resp = api_client.post('/api/v1/support/requests/', payload, format='json')
        assert create_resp.status_code == 201
        ticket_id = create_resp.data['id']
        guest_token = create_resp.data['guest_token']
        assert guest_token != ''

        # Guest retrieves ticket using header
        api_client.credentials(HTTP_X_GUEST_TOKEN=guest_token)
        get_resp = api_client.get(f'/api/v1/support/requests/{ticket_id}/')
        assert get_resp.status_code == 200
        assert get_resp.data['id'] == ticket_id

    def test_learner_cannot_view_other_learner_ticket(self, api_client, learner_user, other_learner):
        # Create ticket for learner_user
        ticket = SupportRequest.objects.create(
            learner=learner_user,
            subject="Private ticket",
            description="Confidential learner problem",
            status="open"
        )

        # other_learner tries to retrieve it
        api_client.force_authenticate(user=other_learner)
        resp = api_client.get(f'/api/v1/support/requests/{ticket.id}/')
        assert resp.status_code == 403

    def test_agent_can_view_all_tickets_and_update_status(self, api_client, learner_user, support_agent):
        ticket = SupportRequest.objects.create(
            learner=learner_user,
            subject="Stuck on assignment",
            description="Need guidance",
            status="open"
        )

        api_client.force_authenticate(user=support_agent)
        # Agent lists tickets
        list_resp = api_client.get('/api/v1/support/requests/')
        assert list_resp.status_code == 200
        assert len(list_resp.data) >= 1

        # Agent assigns to self and moves to in_progress
        status_resp = api_client.patch(
            f'/api/v1/support/requests/{ticket.id}/status/',
            {"status": "in_progress", "assign_to_me": True},
            format='json'
        )
        assert status_resp.status_code == 200
        assert status_resp.data['status'] == 'in_progress'
        assert status_resp.data['assigned_agent_name'] == 'agent_sara'

    def test_regular_learner_cannot_update_ticket_status(self, api_client, learner_user):
        ticket = SupportRequest.objects.create(
            learner=learner_user,
            subject="Test ticket",
            description="Description",
            status="open"
        )
        api_client.force_authenticate(user=learner_user)
        patch_resp = api_client.patch(
            f'/api/v1/support/requests/{ticket.id}/status/',
            {"status": "resolved"},
            format='json'
        )
        assert patch_resp.status_code == 403

    def test_two_way_messaging_between_learner_and_agent(self, api_client, learner_user, support_agent):
        ticket = SupportRequest.objects.create(
            learner=learner_user,
            subject="Question on arrays",
            description="Need explanation",
            status="assigned",
            assigned_agent=support_agent
        )

        # Learner sends message
        api_client.force_authenticate(user=learner_user)
        msg_resp1 = api_client.post(
            f'/api/v1/support/requests/{ticket.id}/messages/',
            {"content": "Are arrays zero-indexed in this course?"},
            format='json'
        )
        assert msg_resp1.status_code == 201
        assert msg_resp1.data['sender_type'] == 'learner'

        # Agent replies
        api_client.force_authenticate(user=support_agent)
        msg_resp2 = api_client.post(
            f'/api/v1/support/requests/{ticket.id}/messages/',
            {"content": "Yes, indexing starts at 0!"},
            format='json'
        )
        assert msg_resp2.status_code == 201
        assert msg_resp2.data['sender_type'] == 'agent'

        # Verify ticket moved to in_progress automatically
        ticket.refresh_from_db()
        assert ticket.status == 'in_progress'

    def test_learner_controlled_screen_share_start_and_stop(self, api_client, learner_user):
        ticket = SupportRequest.objects.create(
            learner=learner_user,
            subject="Live debug request",
            description="Code syntax error",
            status="open"
        )
        api_client.force_authenticate(user=learner_user)

        # Start screen sharing
        start_resp = api_client.post(
            f'/api/v1/support/requests/{ticket.id}/screenshare/',
            {"action": "start"},
            format='json'
        )
        assert start_resp.status_code == 200
        assert start_resp.data['screen_share_active'] is True
        assert 'session_token' in start_resp.data

        ticket.refresh_from_db()
        assert ticket.screen_share_active is True

        # Stop screen sharing
        stop_resp = api_client.post(
            f'/api/v1/support/requests/{ticket.id}/screenshare/',
            {"action": "stop"},
            format='json'
        )
        assert stop_resp.status_code == 200
        assert stop_resp.data['screen_share_active'] is False

        ticket.refresh_from_db()
        assert ticket.screen_share_active is False

    def test_low_bandwidth_screen_snapshot_fallback(self, api_client, learner_user):
        ticket = SupportRequest.objects.create(
            learner=learner_user,
            subject="Slow network screen capture",
            description="3G connection fallback",
            status="open"
        )
        api_client.force_authenticate(user=learner_user)

        snap_resp = api_client.post(
            f'/api/v1/support/requests/{ticket.id}/snapshot/',
            {
                "snapshot_data": "<div id='terminal'>Error: IndentationError</div>",
                "description": "Here is the error on my screen"
            },
            format='json'
        )
        assert snap_resp.status_code == 201
        assert snap_resp.data['is_snapshot'] is True
        assert "IndentationError" in snap_resp.data['snapshot_data']
