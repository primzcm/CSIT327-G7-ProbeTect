from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from .forms import LessonForm
from .models import Lesson


class LessonListView(LoginRequiredMixin, View):
    """List all lessons for the current user."""
    template_name = 'lessons/list.html'

    def get(self, request):
        lessons = Lesson.objects.filter(owner=request.user).select_related('material')
        # Filter by subject if provided
        subject_filter = request.GET.get('subject', '')
        if subject_filter:
            lessons = lessons.filter(subject__icontains=subject_filter)
        
        # Filter by search query if provided
        search_query = request.GET.get('search', '')
        if search_query:
            lessons = lessons.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
        context = {
            'lessons': lessons,
            'subject_filter': subject_filter,
            'search_query': search_query,
            'subjects': Lesson.objects.filter(owner=request.user).exclude(subject='').values_list('subject', flat=True).distinct()
        }
        return render(request, self.template_name, context)


class LessonCreateView(LoginRequiredMixin, View):
    """Create a new lesson entry."""
    template_name = 'lessons/form.html'
    form_class = LessonForm

    def get(self, request):
        form = self.form_class(user=request.user)
        return render(request, self.template_name, {
            'form': form,
            'title': 'Create Lesson'
        })

    def post(self, request):
        form = self.form_class(request.POST, user=request.user)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.owner = request.user
            lesson.save()
            messages.success(request, f'Lesson "{lesson.title}" created successfully.')
            return redirect('lessons:list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Create Lesson'
        })


class LessonEditView(LoginRequiredMixin, View):
    """Edit an existing lesson entry."""
    template_name = 'lessons/form.html'
    form_class = LessonForm

    def get(self, request, pk: int):
        lesson = get_object_or_404(Lesson, pk=pk, owner=request.user)
        form = self.form_class(instance=lesson, user=request.user)
        return render(request, self.template_name, {
            'form': form,
            'lesson': lesson,
            'title': f'Edit: {lesson.title}'
        })

    def post(self, request, pk: int):
        lesson = get_object_or_404(Lesson, pk=pk, owner=request.user)
        form = self.form_class(request.POST, instance=lesson, user=request.user)
        if form.is_valid():
            lesson = form.save()
            messages.success(request, f'Lesson "{lesson.title}" updated successfully.')
            return redirect('lessons:list')
        return render(request, self.template_name, {
            'form': form,
            'lesson': lesson,
            'title': f'Edit: {lesson.title}'
        })


class LessonDeleteView(LoginRequiredMixin, View):
    """Delete a lesson entry."""
    
    def post(self, request, pk: int):
        lesson = get_object_or_404(Lesson, pk=pk, owner=request.user)
        title = lesson.title
        lesson.delete()
        messages.success(request, f'Lesson "{title}" deleted successfully.')
        return redirect('lessons:list')

