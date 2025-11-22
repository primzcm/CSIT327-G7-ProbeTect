from __future__ import annotations

from django.contrib import admin

from .models import Classroom, ClassroomMembership, QuizAssignment


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "code", "created_at")
    search_fields = ("name", "code", "owner__username")
    readonly_fields = ("code", "created_at", "updated_at")


@admin.register(ClassroomMembership)
class ClassroomMembershipAdmin(admin.ModelAdmin):
    list_display = ("classroom", "user", "role", "joined_at")
    list_filter = ("role", "classroom")
    search_fields = ("classroom__name", "user__username")


@admin.register(QuizAssignment)
class QuizAssignmentAdmin(admin.ModelAdmin):
    list_display = ("quiz", "classroom", "created_by", "due_at", "created_at")
    list_filter = ("classroom", "quiz")
    search_fields = ("quiz__title", "classroom__name")
