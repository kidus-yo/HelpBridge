from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from courses.models import Course, CourseSection, Lesson, LessonResource
from platforms.services.context import get_platform_context
from platforms.tenant import get_institution, is_staff


def _can_write(request) -> bool:
    if is_staff(request):
        return True
    context = get_platform_context(request)
    return bool(context and context.has_scope("courses:write"))


def course_queryset(request):
    context = get_platform_context(request)
    qs = Course.objects.select_related("institution").prefetch_related(
        "sections__lessons__resources"
    )
    if context is not None:
        qs = qs.filter(institution_id=context.institution_id)
        if not context.has_scope("courses:write"):
            qs = qs.filter(status=Course.Status.PUBLISHED)
        return qs
    if is_staff(request):
        return qs
    return qs.none()


def get_owned_course(request, course_id) -> Course:
    try:
        course = course_queryset(request).get(id=course_id)
    except Course.DoesNotExist as exc:
        raise PermissionDenied("Course not found for this tenant.") from exc
    return course


@transaction.atomic
def create_course(request, validated_data: dict) -> Course:
    claimed = validated_data.pop("institution", None)
    claimed_id = getattr(claimed, "id", claimed)
    institution = get_institution(request, claimed_id)
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    return Course.objects.create(institution=institution, **validated_data)


@transaction.atomic
def update_course(request, course: Course, validated_data: dict) -> Course:
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    if "institution" in validated_data:
        raise ValidationError({"institution": "Moving a course between institutions is not allowed."})
    for key, value in validated_data.items():
        setattr(course, key, value)
    course.save()
    return course


@transaction.atomic
def set_course_status(request, course: Course, status: str) -> Course:
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    if status == Course.Status.PUBLISHED and not course.title.strip():
        raise ValidationError({"title": "A title is required to publish a course."})
    course.status = status
    course.save(update_fields=["status", "updated_at"])
    return course


def create_section(request, course: Course, validated_data: dict) -> CourseSection:
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    return CourseSection.objects.create(course=course, **validated_data)


def section_queryset(request, course: Course):
    return course.sections.all()


def get_owned_section(request, section_id) -> CourseSection:
    qs = CourseSection.objects.select_related("course__institution")
    context = get_platform_context(request)
    if context is not None:
        qs = qs.filter(course__institution_id=context.institution_id)
    elif not is_staff(request):
        qs = qs.none()
    try:
        return qs.get(id=section_id)
    except CourseSection.DoesNotExist as exc:
        raise PermissionDenied("Section not found for this tenant.") from exc


def create_lesson(request, section: CourseSection, validated_data: dict) -> Lesson:
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    return Lesson.objects.create(section=section, **validated_data)


def lesson_resource_queryset(request, lesson: Lesson):
    qs = lesson.resources.select_related("lesson__section__course__institution")
    context = get_platform_context(request)
    if context is not None:
        return qs.filter(lesson__section__course__institution_id=context.institution_id)
    if is_staff(request):
        return qs
    return qs.none()


def get_owned_lesson(request, lesson_id) -> Lesson:
    qs = Lesson.objects.select_related("section__course__institution")
    context = get_platform_context(request)
    if context is not None:
        qs = qs.filter(section__course__institution_id=context.institution_id)
    elif not is_staff(request):
        qs = qs.none()
    try:
        return qs.get(id=lesson_id)
    except Lesson.DoesNotExist as exc:
        raise PermissionDenied("Lesson not found for this tenant.") from exc


def get_owned_resource(request, resource_id) -> LessonResource:
    qs = LessonResource.objects.select_related("lesson__section__course__institution")
    context = get_platform_context(request)
    if context is not None:
        qs = qs.filter(lesson__section__course__institution_id=context.institution_id)
    elif not is_staff(request):
        qs = qs.none()
    try:
        return qs.get(id=resource_id)
    except LessonResource.DoesNotExist as exc:
        raise PermissionDenied("Resource not found for this tenant.") from exc


@transaction.atomic
def create_lesson_resource(request, lesson: Lesson, validated_data: dict) -> LessonResource:
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    return LessonResource.objects.create(lesson=lesson, **validated_data)


@transaction.atomic
def update_lesson_resource(request, resource: LessonResource, validated_data: dict) -> LessonResource:
    if not _can_write(request):
        raise PermissionDenied("Missing courses:write scope.")
    for key, value in validated_data.items():
        setattr(resource, key, value)
    resource.save()
    return resource


