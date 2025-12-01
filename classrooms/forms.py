from __future__ import annotations

from django import forms

from quizzes.models import Quiz

from .models import Classroom, QuizAssignment
from lessons.models import Lesson


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "placeholder": "e.g., Biology 101 - Period 3",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "rows": 3,
                    "placeholder": "Optional notes for students",
                }
            ),
        }


class ClassroomJoinForm(forms.Form):
    code = forms.CharField(
        max_length=12,
        label="Class code",
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                "placeholder": "Enter class code (e.g., ABC123)",
            }
        ),
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class QuizAssignmentForm(forms.ModelForm):
    class Meta:
        model = QuizAssignment
        fields = ["classroom", "quiz", "title", "due_at", "show_answers"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "placeholder": "Optional title shown to students",
                }
            ),
            "due_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                }
            ),
            "classroom": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                }
            ),
            "quiz": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                }
            ),
            "show_answers": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500",
                }
            ),
        }

    def __init__(self, *args, user=None, classroom=None, quiz=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["classroom"].queryset = user.classrooms.all().order_by("-created_at")
            self.fields["quiz"].queryset = user.quizzes.filter(status=Quiz.Status.READY).order_by("-created_at")
        if classroom is not None:
            self.fields["classroom"].initial = classroom
        if quiz is not None:
            self.fields["quiz"].initial = quiz

        # Prevent picking a due date in the past on the client side where supported
        from django.utils import timezone

        now = timezone.localtime()
        min_value = now.strftime("%Y-%m-%dT%H:%M")
        if "due_at" in self.fields:
            widget = self.fields["due_at"].widget
            attrs = widget.attrs or {}
            attrs["min"] = min_value
            widget.attrs = attrs

    def clean_due_at(self):
        from django.utils import timezone

        due_at = self.cleaned_data.get("due_at")
        if due_at is None:
            return due_at
        # Normalize both to aware datetimes in the same zone
        now = timezone.now()
        if due_at < now:
            raise forms.ValidationError("Due date must be in the future.")
        return due_at


class LessonAssignForm(forms.Form):
    lesson = forms.ModelChoiceField(
        queryset=Lesson.objects.none(),
        label="Select an existing lesson",
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["lesson"].queryset = (
                Lesson.objects.filter(owner=user, classroom__isnull=True).order_by("-created_at")
            )
            self.fields["lesson"].empty_label = "Choose a lesson"
