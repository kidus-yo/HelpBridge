from django.urls import path

from courses.views import (
    CourseDetailView,
    CourseListCreateView,
    CoursePublishView,
    CourseSectionListCreateView,
    CourseUnpublishView,
    LessonListCreateView,
)

urlpatterns = [
    path("courses/", CourseListCreateView.as_view(), name="course-list"),
    path("courses/<uuid:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/<uuid:pk>/publish/", CoursePublishView.as_view(), name="course-publish"),
    path("courses/<uuid:pk>/unpublish/", CourseUnpublishView.as_view(), name="course-unpublish"),
    path("courses/<uuid:course_id>/sections/", CourseSectionListCreateView.as_view(), name="course-section-list"),
    path("sections/<uuid:section_id>/lessons/", LessonListCreateView.as_view(), name="section-lesson-list"),
]
