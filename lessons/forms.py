from __future__ import annotations

from django import forms

from .models import Lesson


class LessonForm(forms.ModelForm):
    """Form for creating and editing lesson entries."""
    
    class Meta:
        model = Lesson
        fields = ['title', 'subject', 'description', 'content', 'scheduled_date', 'material']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200',
                'placeholder': 'Enter lesson title'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200',
                'placeholder': 'e.g., Mathematics, Science'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200',
                'rows': 3,
                'placeholder': 'Brief description of the lesson'
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200',
                'rows': 8,
                'placeholder': 'Lesson content, notes, or plan'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200'
            }),
            'material': forms.Select(attrs={
                'class': 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200'
            })
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = True
        self.fields['content'].required = True
        if user:
            # Only show materials owned by the user
            self.fields['material'].queryset = user.materials.all().order_by('-created_at')
            self.fields['material'].empty_label = "No material (optional)"

