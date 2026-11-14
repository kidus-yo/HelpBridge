import pytest
from datetime import date
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from careers.models import JobListing, AccommodationRequest, JobAlertSubscription
from careers.services import JobAlertService


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user():
    return User.objects.create_superuser(username='staff_recruiter', password='password123')


@pytest.fixture
def learner_user():
    return User.objects.create_user(username='job_seeker', password='password123')


@pytest.fixture
def sample_published_job(staff_user):
    return JobListing.objects.create(
        title="Junior Python / Accessibility Developer",
        organization="ALX Tech Ventures",
        description="Develop accessible web plugins and Django APIs for African learners.",
        location="Addis Ababa (Remote Available)",
        employment_type="full_time",
        remote_policy="remote",
        required_skills=["Python", "Django", "WCAG 2.2", "REST APIs"],
        salary_info="15,000 - 20,000 ETB / month",
        deadline=date(2026, 12, 31),
        application_url="https://example.com/apply/python-dev",
        status="published",
        is_demo=True,
        created_by=staff_user
    )


@pytest.fixture
def sample_draft_job(staff_user):
    return JobListing.objects.create(
        title="Draft Frontend Role",
        organization="Secret Startup",
        description="Not ready for learners yet.",
        location="Addis Ababa",
        status="draft",
        created_by=staff_user
    )


@pytest.mark.django_db
class TestJobListingsAndSearch:

    def test_learner_can_only_view_published_jobs(self, api_client, sample_published_job, sample_draft_job):
        resp = api_client.get('/api/v1/jobs/')
        assert resp.status_code == 200
        titles = [j['title'] for j in resp.data]
        assert sample_published_job.title in titles
        assert sample_draft_job.title not in titles

    def test_learner_cannot_view_draft_job_detail(self, api_client, sample_draft_job):
        resp = api_client.get(f'/api/v1/jobs/{sample_draft_job.id}/')
        assert resp.status_code == 404

    def test_staff_can_view_all_jobs_including_drafts(self, api_client, staff_user, sample_published_job, sample_draft_job):
        api_client.force_authenticate(user=staff_user)
        resp = api_client.get('/api/v1/jobs/')
        assert resp.status_code == 200
        titles = [j['title'] for j in resp.data]
        assert sample_published_job.title in titles
        assert sample_draft_job.title in titles

    def test_learner_cannot_create_jobs(self, api_client, learner_user):
        api_client.force_authenticate(user=learner_user)
        resp = api_client.post('/api/v1/jobs/', {"title": "Fake Job", "organization": "Scam"}, format='json')
        assert resp.status_code == 403

    def test_job_search_filters(self, api_client, sample_published_job):
        # Search by keyword
        resp_kw = api_client.get('/api/v1/jobs/?search=Accessibility')
        assert resp_kw.status_code == 200
        assert len(resp_kw.data) == 1

        # Search by location
        resp_loc = api_client.get('/api/v1/jobs/?location=Addis')
        assert resp_loc.status_code == 200
        assert len(resp_loc.data) == 1

        # Filter no match
        resp_none = api_client.get('/api/v1/jobs/?location=Tokyo')
        assert resp_none.status_code == 200
        assert len(resp_none.data) == 0


@pytest.mark.django_db
class TestGroundedJobQA:

    def test_job_qa_returns_factual_salary_when_present(self, api_client, sample_published_job):
        resp = api_client.post(
            '/api/v1/jobs/questions/',
            {"job_id": str(sample_published_job.id), "question": "What is the salary for this position?"},
            format='json'
        )
        assert resp.status_code == 200
        data = resp.data
        assert data['grounded'] is True
        assert "15,000 - 20,000 ETB" in data['answer']

    def test_job_qa_honest_refusal_when_salary_omitted(self, api_client, staff_user):
        unpaid_job = JobListing.objects.create(
            title="Volunteer Mentor",
            organization="Community Org",
            description="Mentor high schoolers in Python.",
            location="Remote",
            salary_info="",  # Omitted salary
            status="published",
            created_by=staff_user
        )
        resp = api_client.post(
            '/api/v1/jobs/questions/',
            {"job_id": str(unpaid_job.id), "question": "How much does this job pay?"},
            format='json'
        )
        assert resp.status_code == 200
        data = resp.data
        assert data['grounded'] is False
        assert "Salary information is not provided" in data['answer']

    def test_job_qa_returns_deadline_information(self, api_client, sample_published_job):
        resp = api_client.post(
            '/api/v1/jobs/questions/',
            {"job_id": str(sample_published_job.id), "question": "When is the application deadline?"},
            format='json'
        )
        assert resp.status_code == 200
        assert resp.data['grounded'] is True
        assert "December 31, 2026" in resp.data['answer']

    def test_job_qa_rejects_draft_job(self, api_client, sample_draft_job):
        resp = api_client.post(
            '/api/v1/jobs/questions/',
            {"job_id": str(sample_draft_job.id), "question": "What are the requirements?"},
            format='json'
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestInterviewAccommodations:

    def test_submit_accommodation_request_no_medical_diagnosis(self, api_client, learner_user, sample_published_job):
        api_client.force_authenticate(user=learner_user)
        payload = {
            "job_listing": str(sample_published_job.id),
            "functional_needs": ["screen_reader", "extra_time_50"],
            "description": "NVDA screen reader compatible assessment required; need 1.5x time for coding test.",
            "preferred_contact_method": "telegram",
            "contact_details": "@learner_tg"
        }
        resp = api_client.post('/api/v1/accommodations/', payload, format='json')
        assert resp.status_code == 201
        data = resp.data
        assert data['status'] == 'submitted'
        assert data['functional_needs'] == ["screen_reader", "extra_time_50"]

    def test_accommodation_request_is_strictly_private(self, api_client, learner_user, staff_user):
        req = AccommodationRequest.objects.create(
            learner=learner_user,
            functional_needs=["captions_sign"],
            description="Sign language interpreter needed",
            preferred_contact_method="email",
            contact_details="learner@example.com"
        )

        # Another unauthenticated learner cannot see it
        resp_unauth = api_client.get(f'/api/v1/accommodations/{req.id}/')
        assert resp_unauth.status_code == 403

        # Requester can see it
        api_client.force_authenticate(user=learner_user)
        resp_owner = api_client.get(f'/api/v1/accommodations/{req.id}/')
        assert resp_owner.status_code == 200

        # Staff can see and update response
        api_client.force_authenticate(user=staff_user)
        resp_staff = api_client.patch(
            f'/api/v1/accommodations/{req.id}/',
            {"status": "responded", "coordinator_response": "Sign language interpreter confirmed for interview."},
            format='json'
        )
        assert resp_staff.status_code == 200
        assert resp_staff.data['status'] == 'responded'


@pytest.mark.django_db
class TestJobAlertSubscriptionsAndDispatch:

    @patch('channels.notifications.delivery.send_notification')
    def test_job_alert_dispatched_via_shared_channel_adapter(self, mock_notify, staff_user):
        # Create active subscriptions
        sub_sms = JobAlertSubscription.objects.create(
            contact_identity="+251911223344",
            channel="sms",
            keywords=["python", "accessibility"],
            is_active=True
        )
        sub_tg = JobAlertSubscription.objects.create(
            contact_identity="12345678",
            channel="telegram",
            keywords=["django"],
            is_active=True
        )
        # Inactive subscription should be ignored
        JobAlertSubscription.objects.create(
            contact_identity="+251999887766",
            channel="sms",
            keywords=["python"],
            is_active=False
        )

        job = JobListing.objects.create(
            title="Senior Python Django Engineer",
            organization="ALX",
            description="Build accessible apps",
            location="Addis Ababa",
            required_skills=["Python", "Django"],
            status="published",
            created_by=staff_user
        )

        count = JobAlertService.dispatch_alerts_for_job(job)
        assert count == 2
        assert mock_notify.call_count == 2

    def test_unsubscribe_from_job_alerts(self, api_client, learner_user):
        api_client.force_authenticate(user=learner_user)
        sub = JobAlertSubscription.objects.create(
            learner=learner_user,
            contact_identity="+251911000111",
            channel="sms",
            is_active=True
        )

        del_resp = api_client.delete(f'/api/v1/job-alerts/subscriptions/{sub.id}/')
        assert del_resp.status_code == 204
        assert not JobAlertSubscription.objects.filter(id=sub.id).exists()
