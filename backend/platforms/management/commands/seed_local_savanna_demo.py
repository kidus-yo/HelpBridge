import hashlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from courses.models import Course
from knowledge.models import ContentChunk, KnowledgeDocument
from knowledge.storage import get_document_storage
from platforms.models import Institution, Platform, PlatformIntegration
from platforms.services.context import issue_platform_context_token
from platforms.services.credentials import generate_api_key, hash_api_key, key_prefix


DEMO_MATERIALS = {
    "en": (
        "Digital learning helps students develop practical skills. Students should "
        "complete their lessons and practice exercises. Regular practice helps "
        "learners remember new ideas and apply them to real tasks."
    ),
    "am": (
        "ዲጂታል ትምህርት ተማሪዎች ተግባራዊ ክህሎቶችን እንዲያዳብሩ ይረዳል። "
        "ተማሪዎች ትምህርቶቻቸውን ማጠናቀቅና ልምምዶችን መሥራት አለባቸው።"
    ),
}
DEMO_SCOPES = [
    "courses:read",
    "courses:write",
    "knowledge:read",
    "knowledge:write",
    "support:write",
]


class Command(BaseCommand):
    help = "Create a local Savanna-style course demo and print a short-lived widget token."

    def handle(self, *args, **options):
        if settings.DJANGO_ENV == "production" or not settings.DEBUG:
            raise CommandError("This local demo command is available only with DEBUG=True outside production.")

        platform, _ = Platform.objects.get_or_create(
            slug="savanna-local-demo",
            defaults={
                "name": "Savanna Local Demo",
                "platform_type": Platform.PlatformType.LMS,
                "description": "Local-only example LMS integration.",
            },
        )
        institution, _ = Institution.objects.get_or_create(
            slug="savanna-local-demo",
            defaults={
                "name": "Savanna Local Demo Institution",
                "institution_type": Institution.InstitutionType.TRAINING,
                "description": "Local-only sample tenant.",
            },
        )
        if not platform.is_active or not institution.is_active:
            raise CommandError("The local demo platform and institution must be active.")

        api_key = generate_api_key()
        integration, created = PlatformIntegration.objects.get_or_create(
            platform=platform,
            institution=institution,
            name="Local Savanna demo",
            defaults={
                "status": PlatformIntegration.Status.ACTIVE,
                "permitted_scopes": DEMO_SCOPES,
                "api_key_hash": hash_api_key(api_key),
                "api_key_prefix": key_prefix(api_key),
            },
        )
        if not created and integration.status != PlatformIntegration.Status.ACTIVE:
            raise CommandError("The existing local demo integration is not active.")
        if not set(DEMO_SCOPES).issubset(integration.permitted_scopes or []):
            raise CommandError(
                "The existing local demo integration is missing required scopes."
            )

        course, _ = Course.objects.get_or_create(
            institution=institution,
            slug="digital-learning-foundations",
            defaults={
                "title": "Digital Learning Foundations",
                "description": "A short bilingual course for the local widget demo.",
                "language": "en",
                "status": Course.Status.PUBLISHED,
            },
        )
        if course.status != Course.Status.PUBLISHED:
            course.status = Course.Status.PUBLISHED
            course.save(update_fields=["status", "updated_at"])

        for language, text in DEMO_MATERIALS.items():
            self._ensure_material(institution, course, language, text)

        token = issue_platform_context_token(
            integration=integration,
            user_ref="local-demo-learner",
            context_type="course",
            context_id=str(course.id),
            scopes=["courses:read", "knowledge:read", "support:write"],
            preferred_language="en",
        )

        self.stdout.write(self.style.SUCCESS("Local Savanna-style demo is ready."))
        self.stdout.write(f"Course ID: {course.id}")
        self.stdout.write(f"Integration ID: {integration.id}")
        self.stdout.write("Widget page: http://localhost:8001/widget/demo.html")
        if created:
            self.stdout.write(
                "Server-only integration API key (store in Savanna server secrets; "
                "never in browser code):"
            )
            self.stdout.write(api_key)
        else:
            self.stdout.write(
                "This integration already exists; its API key cannot be recovered "
                "here. Use the key already stored by the host server."
            )
        ttl_minutes = settings.PLATFORM_CONTEXT_TTL_SECONDS // 60
        self.stdout.write(
            f"Context token: {token} (expires in {ttl_minutes} minutes)"
        )
        self.stdout.write(
            "Before starting Django, set CORS_ALLOWED_ORIGINS=http://localhost:8001 in .env."
        )

    def _ensure_material(self, institution, course, language, text):
        content = text.encode("utf-8")
        checksum = hashlib.sha256(content).hexdigest()
        document, created = KnowledgeDocument.objects.get_or_create(
            institution=institution,
            course=course,
            checksum=checksum,
            defaults={
                "original_filename": f"savanna-demo-{language}.txt",
                "document_type": KnowledgeDocument.DocumentType.TXT,
                "language": language,
                "processing_status": KnowledgeDocument.ProcessingStatus.COMPLETED,
                "storage_ref": "pending",
                "checksum": checksum,
                "byte_size": len(content),
                "processed_at": timezone.now(),
                "metadata": {"local_demo": True},
            },
        )
        if created or not document.storage_ref or document.storage_ref == "pending":
            storage_ref = get_document_storage().save(
                str(institution.id),
                str(document.id),
                document.original_filename,
                content,
            )
            document.storage_ref = storage_ref
            document.save(update_fields=["storage_ref", "updated_at"])

        ContentChunk.objects.get_or_create(
            document=document,
            chunk_index=0,
            defaults={
                "institution": institution,
                "course": course,
                "chunk_text": text,
                "chunk_index": 0,
                "section_heading": "Practice and learning",
                "language": language,
                "metadata": {"local_demo": True},
            },
        )
        if document.processing_status != KnowledgeDocument.ProcessingStatus.COMPLETED:
            document.processing_status = KnowledgeDocument.ProcessingStatus.COMPLETED
            document.processed_at = timezone.now()
            document.save(update_fields=["processing_status", "processed_at", "updated_at"])
