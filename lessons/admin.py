from django.contrib import admin

from .models import Lesson


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'subject', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['title', 'description', 'content', 'subject']
    readonly_fields = ['created_at', 'updated_at']
