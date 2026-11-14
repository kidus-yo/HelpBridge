from django.contrib import admin

from courses.models import Course, CourseSection, Lesson, LessonResource


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


class SectionInline(admin.TabularInline):
    model = CourseSection
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "institution", "language", "status")
    list_filter = ("status", "language")
    search_fields = ("title", "slug")
    inlines = [SectionInline]


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "position")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "lesson_type", "language")


@admin.register(LessonResource)
class LessonResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "resource_type")
