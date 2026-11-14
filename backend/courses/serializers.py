from rest_framework import serializers

from courses.models import Course, CourseSection, Lesson, LessonResource


class LessonResourceSerializer(serializers.ModelSerializer):
    lesson = serializers.UUIDField(source="lesson_id", read_only=True)

    class Meta:
        model = LessonResource
        fields = [
            "id",
            "lesson",
            "resource_type",
            "title",
            "external_url",
            "file_ref",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "lesson", "created_at", "updated_at"]


class LessonSerializer(serializers.ModelSerializer):
    resources = LessonResourceSerializer(many=True, read_only=True)
    section = serializers.UUIDField(source="section_id", read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "section",
            "title",
            "description",
            "lesson_type",
            "content",
            "external_url",
            "position",
            "language",
            "resources",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "section", "created_at", "updated_at"]


class CourseSectionSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    course = serializers.UUIDField(source="course_id", read_only=True)

    class Meta:
        model = CourseSection
        fields = [
            "id",
            "course",
            "title",
            "description",
            "position",
            "language",
            "lessons",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "course", "created_at", "updated_at"]


class CourseSerializer(serializers.ModelSerializer):
    sections = CourseSectionSerializer(many=True, read_only=True)
    institution = serializers.UUIDField(source="institution_id", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "institution",
            "title",
            "slug",
            "description",
            "language",
            "status",
            "metadata",
            "sections",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
        extra_kwargs = {"institution": {"required": False}}
