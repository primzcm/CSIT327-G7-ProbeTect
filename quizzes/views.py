from __future__ import annotations

import logging
from datetime import datetime, timedelta
from io import BytesIO

from django.contrib import messages
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from materials.models import Material

from .models import Quiz, QuizQuestion
from .services import GeminiError, generate_quiz

logger = logging.getLogger(__name__)


class GenerateQuizView(LoginRequiredMixin, View):
    def post(self, request, material_id: int):
        material = get_object_or_404(Material, pk=material_id, owner=request.user)
        try:
            question_count = int(request.POST.get("question_count", 10))
        except (TypeError, ValueError):
            question_count = 10
        question_count = max(1, min(question_count, 50))
        question_type = request.POST.get("question_type", QuizQuestion.QuestionType.MULTIPLE_CHOICE)
        difficulty = request.POST.get("difficulty", Quiz.Difficulty.MEDIUM)
        timer_minutes = request.POST.get("timer_minutes", "").strip()
        
        # Validate difficulty
        if difficulty not in [Quiz.Difficulty.EASY, Quiz.Difficulty.MEDIUM, Quiz.Difficulty.HARD]:
            difficulty = Quiz.Difficulty.MEDIUM
        
        # Parse timer_minutes (optional)
        timer_value = None
        if timer_minutes:
            try:
                timer_value = int(timer_minutes)
                if timer_value < 0:
                    timer_value = None
            except (ValueError, TypeError):
                timer_value = None

        # Normalize and validate question type values from the form (also accept a few aliases)
        def _normalize_qtype(raw: str | None) -> str:
            if not raw:
                return QuizQuestion.QuestionType.MULTIPLE_CHOICE
            val = str(raw).strip().lower()
            if val in (QuizQuestion.QuestionType.MULTIPLE_CHOICE, 'multiple', 'mc', 'multiple_choice'):
                return QuizQuestion.QuestionType.MULTIPLE_CHOICE
            if val in (QuizQuestion.QuestionType.TRUE_FALSE, 'true/false', 'truefalse', 'tf', 'boolean'):
                return QuizQuestion.QuestionType.TRUE_FALSE
            if val in (QuizQuestion.QuestionType.FILL_IN_BLANK, 'fill-in-blank', 'fill in the blank', 'fib'):
                return QuizQuestion.QuestionType.FILL_IN_BLANK
            return QuizQuestion.QuestionType.MULTIPLE_CHOICE

        # Log the raw values received from the form
        logger.info(f"Form data - question_count: {request.POST.get('question_count')}, question_type: {request.POST.get('question_type')}")

        question_type = _normalize_qtype(question_type)
            
        quiz = Quiz.objects.create(
            owner=request.user,
            material=material,
            status=Quiz.Status.PROCESSING,
            difficulty=difficulty,
            timer_minutes=timer_value,
            settings={
                "question_count": question_count,
                "question_type": question_type,
                "difficulty": difficulty,
                "timer_minutes": timer_value,
            },
        )
        redirect_url = reverse('materials:upload') + '#queue'
        try:
            # Log the values being passed to generate_quiz
            logger.info(f"Calling generate_quiz with question_count={question_count}, question_type={question_type}, difficulty={difficulty}")
            payload = generate_quiz(
                material,
                question_count=question_count,
                question_type=question_type,
                difficulty=difficulty
            )
            reduced_from = payload.pop('reduced_from', None) if isinstance(payload, dict) else None
        except GeminiError as exc:
            quiz.status = Quiz.Status.ERROR
            quiz.error_message = str(exc)
            quiz.save(update_fields=["status", "error_message", "updated_at"])
            messages.error(request, f"Quiz generation failed: {exc}")
        else:
            questions = payload.get("questions", [])
            if reduced_from:
                actual = payload.get('question_count', len(questions))
                messages.warning(
                    request,
                    f'Gemini could only generate {actual} questions instead of {reduced_from}.',
                )
            if not questions:
                quiz.status = Quiz.Status.ERROR
                quiz.error_message = 'Gemini did not return any questions.'
                quiz.save(update_fields=['status', 'error_message', 'updated_at'])
                messages.error(request, 'Gemini did not return any questions.')
            else:
                quiz.title = payload.get('quiz_title', material.title or 'Generated Quiz')
                quiz.model_name = getattr(settings, 'GEMINI_MODEL', '')
                quiz.question_count = payload.get('question_count', len(questions))
                quiz.status = Quiz.Status.READY
                quiz.save(update_fields=['title', 'model_name', 'question_count', 'status', 'updated_at'])
                for index, item in enumerate(questions):
                    choices = item.get("choices", [])
                    correct_answer = ""

                    # Always use the user's selected question type, not what Gemini returns
                    # This ensures the question type matches what the user requested
                    question_type_for_item = question_type

                    if question_type_for_item == QuizQuestion.QuestionType.MULTIPLE_CHOICE:
                        correct_index = item.get("correct_index", 0)
                        if choices:
                            position = min(max(correct_index, 0), max(len(choices) - 1, 0))
                            correct_answer = choices[position]
                    elif question_type_for_item == QuizQuestion.QuestionType.TRUE_FALSE:
                        correct_answer = str(item.get("correct_answer", False)).lower()
                    else:  # fill_in_blank
                        correct_answer = item.get("correct_answer", "")

                    QuizQuestion.objects.create(
                        quiz=quiz,
                        prompt=item.get("prompt", ""),
                        choices=choices,
                        correct_answer=correct_answer,
                        explanation=item.get("explanation", ""),
                        order=index,
                        question_type=question_type_for_item,
                    )
                messages.success(request, "Quiz generated successfully.")
                redirect_url = reverse('quizzes:detail', args=[quiz.pk])
        return redirect(redirect_url)


class QuizListView(LoginRequiredMixin, View):
    template_name = 'quizzes/list.html'

    def get(self, request, material_id: int | None = None):
        from django.db.models import Q
        
        quizzes = Quiz.objects.filter(owner=request.user).select_related('material')
        material = None
        if material_id:
            quizzes = quizzes.filter(material_id=material_id)
            material = get_object_or_404(Material, pk=material_id, owner=request.user)
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            quizzes = quizzes.filter(
                Q(title__icontains=search_query) |
                Q(material__title__icontains=search_query)
            )
        
        # Filter by status
        status_filter = request.GET.get('status', '')
        if status_filter:
            quizzes = quizzes.filter(status=status_filter)
        
        # Filter by material
        material_filter = request.GET.get('material', '')
        if material_filter:
            quizzes = quizzes.filter(material_id=material_filter)
        
        quizzes = quizzes.order_by('-created_at')
        
        # Get available materials for filter dropdown
        available_materials = Material.objects.filter(owner=request.user).order_by('-created_at')
        
        return render(request, self.template_name, {
            'quizzes': quizzes,
            'material': material,
            'search_query': search_query,
            'status_filter': status_filter,
            'material_filter': material_filter,
            'available_materials': available_materials,
            'status_choices': Quiz.Status.choices,
        })


class QuizDetailView(LoginRequiredMixin, View):
    template_name = 'quizzes/detail.html'

    def get_quiz(self, request, pk: int) -> Quiz:
        return get_object_or_404(
            Quiz.objects.prefetch_related('questions').select_related('material'),
            pk=pk,
            owner=request.user,
        )

    def get(self, request, pk: int):
        quiz = self.get_quiz(request, pk)
        questions = list(quiz.questions.all())
        entries = [{'question': question, 'result': None} for question in questions]
        return render(request, self.template_name, {
            'quiz': quiz,
            'questions': questions,
            'entries': entries,
        })

    def post(self, request, pk: int):
        quiz = self.get_quiz(request, pk)
        questions = list(quiz.questions.all())
        entries = []
        score = 0
        for question in questions:
            field_name = f'q_{question.id}'
            user_answer = request.POST.get(field_name, '').strip()
            correct_answer = (question.correct_answer or '').strip()
            if question.choices:
                is_correct = user_answer == correct_answer
            else:
                is_correct = user_answer.lower() == correct_answer.lower() if user_answer and correct_answer else False
            if is_correct:
                score += 1
            entries.append({
                'question': question,
                'result': {
                    'user_answer': user_answer,
                    'correct': is_correct,
                },
            })
        total = len(entries) or 1
        percent = round((score / total) * 100, 1)
        return render(request, self.template_name, {
            'quiz': quiz,
            'questions': questions,
            'entries': entries,
            'submitted': True,
            'score': score,
            'total': total,
            'percent': percent,
        })


class QuizExportPDFView(LoginRequiredMixin, View):
    """Export quiz as PDF."""
    def get(self, request, pk: int):
        quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#4F46E5',
                spaceAfter=12,
            )
            story.append(Paragraph(quiz.title or "Quiz", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Quiz info
            info_text = f"Material: {quiz.material.title}<br/>"
            info_text += f"Difficulty: {quiz.get_difficulty_display()}<br/>"
            info_text += f"Questions: {quiz.question_count}"
            story.append(Paragraph(info_text, styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Questions (without answers - for student use)
            for idx, question in enumerate(quiz.questions.all(), 1):
                story.append(Paragraph(f"<b>Question {idx}:</b> {question.prompt}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
                
                if question.question_type == 'multiple_choice' and question.choices:
                    # Show choices with letters (A, B, C, D, etc.)
                    choice_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
                    for i, choice in enumerate(question.choices):
                        if i < len(choice_letters):
                            story.append(Paragraph(f"  {choice_letters[i]}. {choice}", styles['Normal']))
                elif question.question_type == 'true_false':
                    story.append(Paragraph("  A. True", styles['Normal']))
                    story.append(Paragraph("  B. False", styles['Normal']))
                else:
                    # Fill in the blank - show blank line
                    story.append(Paragraph("  Answer: _______________________", styles['Normal']))
                
                story.append(Spacer(1, 0.3*inch))  # Space for student to write answer
            
            doc.build(story)
            buffer.seek(0)
            
            response = HttpResponse(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="quiz_{quiz.pk}.pdf"'
            return response
        except ImportError:
            messages.error(request, "PDF export requires 'reportlab' package. Please install it.")
            return redirect('quizzes:detail', pk=pk)


class QuizExportDOCXView(LoginRequiredMixin, View):
    """Export quiz as DOCX."""
    def get(self, request, pk: int):
        quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
        
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            doc = Document()
            
            # Title
            title = doc.add_heading(quiz.title or "Quiz", 0)
            title.alignment = WD_ALIGN_PARAGRAPH.LEFT
            title.runs[0].font.color.rgb = RGBColor(79, 70, 229)
            
            # Quiz info
            doc.add_paragraph(f"Material: {quiz.material.title}")
            doc.add_paragraph(f"Difficulty: {quiz.get_difficulty_display()}")
            doc.add_paragraph(f"Questions: {quiz.question_count}")
            doc.add_paragraph()  # Blank line
            
            # Questions (without answers - for student use)
            for idx, question in enumerate(quiz.questions.all(), 1):
                doc.add_heading(f"Question {idx}", level=2)
                doc.add_paragraph(question.prompt)
                
                if question.question_type == 'multiple_choice' and question.choices:
                    # Show choices with letters (A, B, C, D, etc.)
                    choice_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
                    for i, choice in enumerate(question.choices):
                        if i < len(choice_letters):
                            doc.add_paragraph(f"{choice_letters[i]}. {choice}")
                elif question.question_type == 'true_false':
                    doc.add_paragraph("A. True")
                    doc.add_paragraph("B. False")
                else:
                    # Fill in the blank - show blank line
                    doc.add_paragraph("Answer: _______________________")
                
                doc.add_paragraph()  # Blank line for student to write answer
                doc.add_paragraph()  # Extra spacing
            
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="quiz_{quiz.pk}.docx"'
            return response
        except ImportError:
            messages.error(request, "DOCX export requires 'python-docx' package. Please install it.")
            return redirect('quizzes:detail', pk=pk)
