"""
Management command to seed realistic demo data for Career Gateway and Support Helpdesk.
Designed for judge evaluation and automated demo walkthroughs.
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from careers.models import JobListing, AccommodationRequest, JobAlertSubscription
from support.models import SupportRequest, SupportMessage


class Command(BaseCommand):
    help = "Seeds realistic demo data for testing Yensew's Support & Careers modules."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Support & Careers demo data...")

        # 1. Create or get SupportAgent group and agent user
        agent_group, _ = Group.objects.get_or_create(name='SupportAgent')
        agent_user, created = User.objects.get_or_create(
            username='agent_sara',
            defaults={
                'first_name': 'Sara',
                'last_name': 'Kebede',
                'email': 'sara.kebede@alx.app',
                'is_staff': True
            }
        )
        if created:
            agent_user.set_password('password123')
            agent_user.save()
        agent_user.groups.add(agent_group)

        # Create demo learner user
        learner_user, _ = User.objects.get_or_create(
            username='dawit_learner',
            defaults={
                'first_name': 'Dawit',
                'last_name': 'Tadesse',
                'email': 'dawit.t@alx.app'
            }
        )

        # 2. Seed Realistic Ethiopian Demo Job Listings
        demo_jobs = [
            {
                'title': 'Junior Accessibility QA Tester',
                'organization': 'EthioTech Innovations',
                'description': (
                    'Test educational software and web apps for WCAG 2.2 AA compliance using screen readers '
                    '(NVDA, TalkBack) and keyboard navigation. Work with frontend engineers to remediate contrast '
                    'and ARIA live region issues.'
                ),
                'location': 'Addis Ababa (Remote Available)',
                'employment_type': 'full_time',
                'remote_policy': 'remote',
                'required_skills': ['Screen Readers (NVDA/TalkBack)', 'WCAG 2.2 AA', 'Semantic HTML', 'Amharic'],
                'salary_info': '18,000 - 24,000 ETB / month',
                'deadline': date.today() + timedelta(days=45),
                'application_url': 'https://ethiotech.example.com/apply/accessibility-qa',
                'status': 'published',
                'is_demo': True
            },
            {
                'title': 'Backend Python / Django Intern',
                'organization': 'ALX Africa Ventures',
                'description': (
                    'Build RESTful APIs and asynchronous notification dispatchers for multilingual educational '
                    'assistants. Experience with Django REST Framework and unit testing is preferred.'
                ),
                'location': 'Addis Ababa (Bole Medhanialem)',
                'employment_type': 'internship',
                'remote_policy': 'hybrid',
                'required_skills': ['Python', 'Django', 'PostgreSQL', 'REST APIs', 'Git'],
                'salary_info': '15,000 - 20,000 ETB / month',
                'deadline': date.today() + timedelta(days=30),
                'application_url': 'https://alxventures.example.com/careers/backend-intern',
                'status': 'published',
                'is_demo': True
            },
            {
                'title': 'Multilingual Data Annotation Specialist',
                'organization': 'Addis AI Lab',
                'description': (
                    'Annotate and evaluate Ethiopic NLP datasets in Amharic, Afaan Oromo, and Tigrinya for educational '
                    'tutor models. Ensure faithful transcription and cultural nuance.'
                ),
                'location': 'Remote (Ethiopia)',
                'employment_type': 'part_time',
                'remote_policy': 'remote',
                'required_skills': ['Amharic', 'Afaan Oromo', 'Text Annotation', 'Attention to Detail'],
                'salary_info': '12,000 - 16,000 ETB / month',
                'deadline': date.today() + timedelta(days=60),
                'application_url': 'https://addisai.example.com/jobs/annotator',
                'status': 'published',
                'is_demo': True
            },
            {
                'title': 'Draft Senior Systems Engineer',
                'organization': 'FinTech Ethiopia',
                'description': 'Internal draft posting for infrastructure development.',
                'location': 'Addis Ababa',
                'employment_type': 'full_time',
                'remote_policy': 'on_site',
                'status': 'draft',
                'is_demo': True
            }
        ]

        created_jobs = []
        for job_data in demo_jobs:
            job, _ = JobListing.objects.get_or_create(
                title=job_data['title'],
                organization=job_data['organization'],
                defaults={**job_data, 'created_by': agent_user}
            )
            created_jobs.append(job)

        # 3. Seed Realistic Support Requests & Messages
        # Ticket 1: Accessibility concern (Open)
        t1, _ = SupportRequest.objects.get_or_create(
            subject='TalkBack screen reader not reading Ethiopic text correctly',
            defaults={
                'learner': learner_user,
                'category': 'accessibility',
                'priority': 'high',
                'status': 'open',
                'preferred_assistance_mode': 'chat',
                'language': 'am',
                'learner_consent_chat_history': True,
                'description': (
                    'When navigating the course page with Android TalkBack, Ethiopic Fidel characters in code snippets '
                    'are being skipped or pronounced as raw Unicode points.'
                )
            }
        )

        # Ticket 2: Course escalation with agent conversation (In Progress)
        t2, t2_created = SupportRequest.objects.get_or_create(
            subject='Confused about recursion base condition in Python',
            defaults={
                'learner': learner_user,
                'category': 'course',
                'priority': 'normal',
                'status': 'in_progress',
                'assigned_agent': agent_user,
                'preferred_assistance_mode': 'chat',
                'language': 'en',
                'learner_consent_chat_history': True,
                'description': 'My recursive function hits maximum recursion depth exceeded. Can someone review my logic?'
            }
        )
        if t2_created:
            SupportMessage.objects.create(
                support_request=t2,
                sender_type='learner',
                sender=learner_user,
                content='Here is my function: def factorial(n): return n * factorial(n-1)'
            )
            SupportMessage.objects.create(
                support_request=t2,
                sender_type='agent',
                sender=agent_user,
                content=(
                    'Hello Dawit! Notice that you need a base condition like "if n <= 1: return 1" to stop '
                    'the function from recursing infinitely.'
                )
            )

        # 4. Seed Interview Accommodation Requests (Zero-Diagnosis Principle)
        acc_job = created_jobs[0] if created_jobs else None
        AccommodationRequest.objects.get_or_create(
            learner=learner_user,
            job_listing=acc_job,
            defaults={
                'functional_needs': ['screen_reader', 'extra_time_50'],
                'description': (
                    'Screen-reader compatible code editor required for live assessment; requesting 1.5x extended time '
                    'due to speech synthesizer navigation.'
                ),
                'preferred_contact_method': 'telegram',
                'contact_details': '@dawit_t_alx',
                'status': 'reviewing'
            }
        )

        # 5. Seed Job Alert Subscriptions
        JobAlertSubscription.objects.get_or_create(
            learner=learner_user,
            contact_identity='+251911223344',
            defaults={
                'channel': 'sms',
                'keywords': ['python', 'accessibility'],
                'location_preference': 'Addis Ababa',
                'is_active': True
            }
        )
        JobAlertSubscription.objects.get_or_create(
            learner=learner_user,
            contact_identity='123456789',
            defaults={
                'channel': 'telegram',
                'keywords': ['django', 'qa'],
                'is_active': True
            }
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(f"- Created Support Agent: agent_sara (password: password123)")
        self.stdout.write(f"- Created {len(created_jobs)} Job Listings (including published Ethiopian tech roles & draft)")
        self.stdout.write(f"- Created Sample Support Tickets (accessibility issue & course Q&A)")
        self.stdout.write(f"- Created Sample Accommodation Request (functional adjustments)")
        self.stdout.write(f"- Created Sample Job Alert Subscriptions (SMS & Telegram)")
