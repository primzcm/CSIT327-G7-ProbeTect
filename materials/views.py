from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .forms import MaterialUploadForm
from .models import Material
from .supabase import SupabaseStorageError, upload_file
from quizzes.models import QuizQuestion


class MaterialUploadView(LoginRequiredMixin, View):
    template_name = "materials/upload.html"
    form_class = MaterialUploadForm

    def get(self, request):
        form = self.form_class()
        materials = request.user.materials.all()[:10]
        return render(request, self.template_name, {
            "form": form,
            "materials": materials,
            "QuizQuestion": QuizQuestion
        })

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        materials = request.user.materials.all()[:10]
        if form.is_valid():
            pdf_file = form.cleaned_data["pdf"]
            try:
                storage_path, public_url = upload_file(pdf_file, owner_id=request.user.id)
            except SupabaseStorageError as exc:
                form.add_error("pdf", str(exc))
            else:
                material = Material.objects.create(
                    owner=request.user,
                    title=form.cleaned_data.get("title", ""),
                    subject=form.cleaned_data.get("subject", ""),
                    description=form.cleaned_data.get("description", ""),
                    visibility=form.cleaned_data.get("visibility"),
                    storage_path=storage_path,
                    public_url=public_url,
                    content_type=getattr(pdf_file, "content_type", ""),
                    file_size=getattr(pdf_file, "size", None),
                    original_filename=pdf_file.name,
                )
                material.refresh_from_db()  # ensure title fallback applied
                messages.success(request, "PDF uploaded. We will start processing it shortly.")
                return redirect("materials:upload")
        if form.errors:
            messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {
            "form": form,
            "materials": materials,
            "QuizQuestion": QuizQuestion
        })
