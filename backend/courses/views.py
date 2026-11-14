from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from courses.serializers import (
    CourseSectionSerializer,
    CourseSerializer,
    LessonResourceSerializer,
    LessonSerializer,
)
from courses.services import (
    course_queryset,
    create_course,
    create_lesson,
    create_lesson_resource,
    create_section,
    get_owned_course,
    get_owned_lesson,
    get_owned_resource,
    get_owned_section,
    lesson_resource_queryset,
    set_course_status,
    update_course,
    update_lesson_resource,
)
from platforms.authentication import PlatformContextAuthentication
from platforms.permissions import CourseAccessPermission


class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]

    def get_queryset(self):
        return course_queryset(self.request)

    def perform_create(self, serializer):
        course = create_course(self.request, serializer.validated_data)
        serializer.instance = course


class CourseDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CourseSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return course_queryset(self.request)

    def perform_update(self, serializer):
        course = update_course(self.request, serializer.instance, serializer.validated_data)
        serializer.instance = course


class CoursePublishView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]

    def post(self, request, pk):
        course = get_owned_course(request, pk)
        course = set_course_status(request, course, Course.Status.PUBLISHED)
        return Response(CourseSerializer(course).data)


class CourseUnpublishView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]

    def post(self, request, pk):
        course = get_owned_course(request, pk)
        course = set_course_status(request, course, Course.Status.DRAFT)
        return Response(CourseSerializer(course).data)


class CourseSectionListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseSectionSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]

    def get_queryset(self):
        course = get_owned_course(self.request, self.kwargs["course_id"])
        return course.sections.all()

    def perform_create(self, serializer):
        course = get_owned_course(self.request, self.kwargs["course_id"])
        section = create_section(self.request, course, serializer.validated_data)
        serializer.instance = section


class LessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]

    def get_queryset(self):
        section = get_owned_section(self.request, self.kwargs["section_id"])
        return section.lessons.all()

    def perform_create(self, serializer):
        section = get_owned_section(self.request, self.kwargs["section_id"])
        lesson = create_lesson(self.request, section, serializer.validated_data)
        serializer.instance = lesson


class LessonResourceListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonResourceSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]

    def get_queryset(self):
        lesson = get_owned_lesson(self.request, self.kwargs["lesson_id"])
        return lesson_resource_queryset(self.request, lesson)

    def perform_create(self, serializer):
        lesson = get_owned_lesson(self.request, self.kwargs["lesson_id"])
        resource = create_lesson_resource(self.request, lesson, serializer.validated_data)
        serializer.instance = resource


class LessonResourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LessonResourceSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [CourseAccessPermission]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return self.get_object().lesson.resources.all()

    def get_object(self):
        return get_owned_resource(self.request, self.kwargs["resource_id"])

    def perform_update(self, serializer):
        resource = update_lesson_resource(self.request, self.get_object(), serializer.validated_data)
        serializer.instance = resource

    def perform_destroy(self, instance):
        instance.delete()
