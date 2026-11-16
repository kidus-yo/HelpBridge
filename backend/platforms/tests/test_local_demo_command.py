from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings

from courses.models import Course
from knowledge.models import ContentChunk
from platforms.services.context import parse_and_validate_token


class LocalSavannaDemoCommandTests(TestCase):
    def test_command_seeds_a_published_bilingual_course_and_context_token(self):
        output = []
        with TemporaryDirectory() as media_root:
            with override_settings(
                MEDIA_ROOT=Path(media_root),
                DEBUG=True,
                DJANGO_ENV="development",
            ):
                call_command("seed_local_savanna_demo", stdout=CaptureOutput(output))

        course = Course.objects.get(slug="digital-learning-foundations")
        self.assertEqual(course.status, Course.Status.PUBLISHED)
        self.assertEqual(ContentChunk.objects.filter(course=course).count(), 2)

        token_line = next(
            line for line in output if line.startswith("Context token: ")
        )
        token = token_line.removeprefix("Context token: ").split(" (expires", 1)[0]
        context = parse_and_validate_token(token)
        self.assertEqual(context.context_type, "course")
        self.assertEqual(context.context_id, str(course.id))
        self.assertIn("support:write", context.scopes)


class CaptureOutput:
    def __init__(self, lines):
        self.lines = lines

    def write(self, message):
        self.lines.append(str(message))
