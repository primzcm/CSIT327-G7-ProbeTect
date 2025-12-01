from __future__ import annotations

from django import forms

from .models import Lesson


class LessonForm(forms.ModelForm):
    """Form for creating and editing lesson entries."""

    # Optional inline upload so instructors can attach a new material while creating a lesson
    new_material_pdf = forms.FileField(
        label="Upload new material (PDF)",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "block w-full cursor-pointer rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                "accept": "application/pdf",
            }
        ),
        help_text="Optional. Upload a PDF up to 25 MB to attach as this lesson's material.",
    )

    class Meta:
        model = Lesson
        fields = ["title", "subject", "description", "content", "material", "classroom"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "placeholder": "Enter lesson title",
                }
            ),
            "subject": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "placeholder": "e.g., Mathematics, Science",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "rows": 3,
                    "placeholder": "Brief description of the lesson",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200",
                    "rows": 8,
                    "placeholder": "Lesson content, notes, or plan",
                }
            ),
            "material": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                }
            ),
            "classroom": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = True
        self.fields["content"].required = True
        if user:
            # Only show materials owned by the user
            self.fields["material"].queryset = user.materials.all().order_by("-created_at")
            self.fields["material"].empty_label = "No material (optional)"
            self.fields["classroom"].queryset = user.classrooms.all().order_by("-created_at")
            self.fields["classroom"].empty_label = "No class (optional)"

    def clean_new_material_pdf(self):
        pdf = self.cleaned_data.get("new_material_pdf")
        if not pdf:
            return pdf
        if pdf.size > 25 * 1024 * 1024:
            raise forms.ValidationError("Please upload a PDF smaller than 25 MB.")
        if pdf.content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}:
            raise forms.ValidationError("Please upload a valid PDF document.")
        return pdf
