from __future__ import annotations

import logging
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
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
            settings={
                "question_count": question_count,
                "question_type": question_type
            },
        )
        redirect_url = reverse('materials:upload') + '#queue'
        try:
            # Log the values being passed to generate_quiz
            logger.info(f"Calling generate_quiz with question_count={question_count}, question_type={question_type}")
            payload = generate_quiz(
                material,
                question_count=question_count,
                question_type=question_type
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
        quizzes = Quiz.objects.filter(owner=request.user).select_related('material')
        material = None
        if material_id:
            quizzes = quizzes.filter(material_id=material_id)
            material = get_object_or_404(Material, pk=material_id, owner=request.user)
        quizzes = quizzes.order_by('-created_at')
        return render(request, self.template_name, {
            'quizzes': quizzes,
            'material': material,
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
