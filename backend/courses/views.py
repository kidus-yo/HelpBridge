from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from courses.serializers import CourseSectionSerializer, CourseSerializer, LessonSerializer
from courses.services import (
    course_queryset,
    create_course,
    create_lesson,
    create_section,
    get_owned_course,
    get_owned_section,
    set_course_status,
    update_course,
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
