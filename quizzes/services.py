from __future__ import annotations

import json
import logging
import re
import textwrap
import urllib.error
import urllib.request
from io import BytesIO

from django.conf import settings

from materials.supabase import download_file
from .models import QuizQuestion

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - handled at runtime
    PdfReader = None  # type: ignore[misc]


class GeminiError(RuntimeError):
    """Raised when Gemini quiz generation fails."""


QUESTION_BLOCK_RE = re.compile(r'("questions"\s*:\s*\[)(.*?)(\]\s*[},])', re.S)
DEFAULT_MAX_TOKENS = 4096  # Increased to handle more questions


def _pdf_bytes(material) -> bytes:
    if not material.storage_path:
        raise GeminiError("Material is missing a Supabase storage path.")
    try:
        return download_file(material.storage_path)
    except Exception as exc:  # pragma: no cover
        raise GeminiError(f"Unable to download PDF: {exc}") from exc


def extract_text(material) -> str:
    if PdfReader is None:
        raise GeminiError("pypdf is not installed. Run 'pip install pypdf'.")
    reader = PdfReader(BytesIO(_pdf_bytes(material)))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # pragma: no cover
            continue
    text = "\n".join(filter(None, parts))
    if not text.strip():
        raise GeminiError("Could not extract text from PDF.")
    return text


def chunk_text(text: str, max_chars: int = 12000) -> list[str]:  # Increased max_chars
    text = textwrap.dedent(text).strip()
    if len(text) <= max_chars:
        return [text]
    
    # Split into paragraphs first
    paragraphs = text.split('\n\n')
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    
    for para in paragraphs:
        para_len = len(para) + 2  # +2 for newlines
        if current_len + para_len > max_chars and current:
            chunks.append('\n\n'.join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len
            
    if current:
        chunks.append('\n\n'.join(current))
    return chunks


def build_prompt(chunks: list[str], question_count: int, question_type: str | None = None) -> str:
    joined = "\n\n".join(chunks[:5])  # Increased to include more context
    
    prompt_template = ""
    if question_type == QuizQuestion.QuestionType.MULTIPLE_CHOICE:
        prompt_template = textwrap.dedent("""
            You are an AI tutor. Read the provided study material and create EXACTLY {question_count} multiple-choice questions.
            IMPORTANT RULES:
            1. You MUST generate exactly {question_count} questions - no more, no less
            2. Every question MUST be multiple choice - no other question types allowed
            3. Each question MUST have exactly four answer choices
            4. Include explanations referencing the source material
            
            Return STRICT JSON that matches this structure:
            {{
              "quiz_title": "string",
              "questions": [
                {{
                  "type": "multiple_choice",
                  "prompt": "string",
                  "choices": ["choice A", "choice B", "choice C", "choice D"],
                  "correct_index": 0,
                  "explanation": "string"
                }}
              ]
            }}
        """)
    elif question_type == QuizQuestion.QuestionType.TRUE_FALSE:
        prompt_template = textwrap.dedent("""
            You are an AI tutor. Read the provided study material and create EXACTLY {question_count} true/false questions.
            IMPORTANT RULES:
            1. You MUST generate exactly {question_count} questions - no more, no less
            2. Every question MUST be true/false - no other question types allowed
            3. The response for each question must be either true or false (boolean)
            4. Include explanations referencing the source material
            
            Return STRICT JSON that matches this structure:
            {{
              "quiz_title": "string",
              "questions": [
                {{
                  "type": "true_false",
                  "prompt": "string",
                  "correct_answer": true,
                  "explanation": "string"
                }}
              ]
            }}
        """)
    elif question_type == QuizQuestion.QuestionType.FILL_IN_BLANK:
        prompt_template = textwrap.dedent("""
            You are an AI tutor. Read the provided study material and create EXACTLY {question_count} fill-in-the-blank questions.
            IMPORTANT RULES:
            1. You MUST generate exactly {question_count} questions - no more, no less
            2. Every question MUST be fill-in-the-blank - no other question types allowed
            3. Each question must use ___ to mark where the answer should go
            4. The correct_answer must be a single word or short phrase that fits in the blank
            5. Include explanations referencing the source material
            
            Return STRICT JSON that matches this structure:
            {{
              "quiz_title": "string", 
              "questions": [
                {{
                  "type": "fill_in_blank",
                  "prompt": "Complete this statement: The process of ___ is important.",
                  "choices": [],
                  "correct_answer": "photosynthesis",
                  "explanation": "string"
                }}
              ]
            }}
        """)
    else:
        prompt_template = textwrap.dedent("""
            You are an AI tutor. Read the provided study material and create {question_count} multiple choice questions.
            Include explanations referencing the source material.
            Return STRICT JSON that matches this structure:
            {{
              "quiz_title": "string",
              "questions": [
                {{
                  "type": "multiple_choice",
                  "prompt": "string",
                  "choices": ["choice A", "choice B", "choice C", "choice D"],
                  "correct_index": 0,
                  "explanation": "string"
                }}
              ]
            }}
              ]
            }}
        """)
    
    prompt = prompt_template.strip() + "\n\nRequirements:\n"
    prompt += "- Output must be valid JSON (RFC 8259) with no markdown, comments, or trailing commas.\n"
    prompt += "- Insert a comma between question objects except after the final one.\n"
    prompt += "- Do not introduce extra sections or keys beyond the schema above.\n"
    prompt += "- Use plain Unicode characters (e.g., ?) and do not emit literal \\\\u escapes.\n\n"
    prompt += f"Material:\n{joined}"
    
    return prompt.format(question_count=question_count)



def _repair_json(cleaned: str) -> str | None:
    match = QUESTION_BLOCK_RE.search(cleaned)
    if not match:
        return None
    prefix, body, suffix = match.groups()
    patched_body, replacements = re.subn(r'}\s*(?=\{\s*"prompt")', '}, ', body)
    if replacements == 0:
        return None
    candidate = f"{cleaned[:match.start()]}{prefix}{patched_body}{suffix}{cleaned[match.end():]}"
    try:
        json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return candidate


def _sanitize_json_with_gemini(cleaned: str) -> str | None:
    prompt = textwrap.dedent(
        """
        You are a JSON formatter. Convert the provided text into valid JSON matching the schema below. Output only the corrected JSON and nothing else.

        Schema:
        {
          "quiz_title": "string",
          "questions": [
            {
              "type": "multiple_choice",
              "prompt": "string",
              "choices": ["string", "string", "string", "string"],
              "correct_index": 0,
              "explanation": "string"
            },
            {
              "type": "true_false",
              "prompt": "string",
              "correct_answer": "true",
              "explanation": "string"
            },
            {
              "type": "fill_in_blank",
              "prompt": "string",
              "correct_answer": "string",
              "explanation": "string"
            }
          ]
        }

        Text to repair:
        ```
        {payload}
        ```
        """
    ).format(payload=cleaned)
    try:
        text, _ = _make_gemini_request(prompt, max_output_tokens=1024)
    except GeminiError:
        return None
    sanitized = _extract_json_payload(text)
    try:
        json.loads(sanitized)
    except json.JSONDecodeError:
        return None
    return sanitized


def _extract_json_payload(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and start < end:
        return cleaned[start : end + 1]
    return cleaned


def _make_gemini_request(prompt: str, *, max_output_tokens: int = DEFAULT_MAX_TOKENS) -> tuple[str, dict]:
    api_key = settings.GEMINI_API_KEY
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured.")
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,  # Increased to encourage completion
            "maxOutputTokens": max_output_tokens,
            "topP": 0.8,  # Added for better generation
            "topK": 40
        },
    }
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")
        raise GeminiError(f"Gemini API error {exc.code}: {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise GeminiError(f"Gemini network error: {exc.reason}") from exc

    payload = json.loads(raw)
    candidates = payload.get("candidates") or []
    if not candidates:
        raise GeminiError(f"Unexpected response from Gemini API: {payload}")
    candidate = candidates[0]
    content = candidate.get("content", {})
    parts = content.get("parts") or []
    if not parts or "text" not in parts[0]:
        raise GeminiError(f"Unexpected response from Gemini API: {payload}")
    text_output = parts[0]["text"]
    finish_reason = candidate.get("finishReason", "")
    if finish_reason and finish_reason.upper() != "STOP":
        raise GeminiError(f"Gemini finished with status {finish_reason} and returned incomplete data.")
    return text_output, payload


def call_gemini(prompt: str, max_output_tokens: int = DEFAULT_MAX_TOKENS) -> dict:
    text_output, _ = _make_gemini_request(prompt, max_output_tokens=max_output_tokens)
    cleaned = _extract_json_payload(text_output)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        cleaned = re.sub(r"\\u(?![0-9a-fA-F]{4})", "", cleaned)
        cleaned = cleaned.replace("\\\\", "\\")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            repaired = _repair_json(cleaned)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    cleaned = repaired
            sanitized = _sanitize_json_with_gemini(cleaned)
            if sanitized:
                return json.loads(sanitized)
            snippet = cleaned[:200]
            raise GeminiError(f"Gemini returned invalid JSON that could not be repaired. Payload snippet: {snippet}")


def generate_quiz(material, *, question_count: int = 5, question_type: str | None = None) -> dict:
    logger.info(f"generate_quiz called with question_count={question_count}, question_type={question_type}")
    question_count = max(1, min(question_count, 50))  # Allow up to 50 questions
    text = extract_text(material)
    chunks = chunk_text(text)
    
    # Calculate max tokens based on question count
    base_tokens = DEFAULT_MAX_TOKENS
    scaling_factor = max(1.0, question_count / 5) * 2  # Double the scaling for more questions
    max_tokens = int(base_tokens * scaling_factor * 1.5)  # Add 50% buffer
    
    # Ensure question type is valid
    if question_type not in (QuizQuestion.QuestionType.MULTIPLE_CHOICE, 
                           QuizQuestion.QuestionType.TRUE_FALSE,
                           QuizQuestion.QuestionType.FILL_IN_BLANK):
        logger.warning(f"Invalid question type {question_type}, defaulting to multiple choice")
        question_type = QuizQuestion.QuestionType.MULTIPLE_CHOICE
    
    prompt = build_prompt(chunks, question_count, question_type)
    try:
        quiz = call_gemini(prompt, max_output_tokens=max_tokens)
        # Verify we got the requested number of questions
        actual_count = len(quiz.get('questions', []))
        if actual_count < question_count:
            # Try again with even more tokens
            max_tokens = int(max_tokens * 1.5)  # Increase by another 50%
            quiz = call_gemini(prompt, max_output_tokens=max_tokens)
            actual_count = len(quiz.get('questions', []))
        return quiz
    except GeminiError as exc:
        message = str(exc)
        if 'MAX_TOKENS' in message:
            # Calculate a more modest reduction
            reduced_count = max(question_count - 5, 5)  # Reduce by 5 but keep at least 5
            # Pass question_type in retry attempt
            prompt = build_prompt(chunks, reduced_count, question_type)
            # Calculate tokens for retry - use 2x base for larger sets
            retry_tokens = DEFAULT_MAX_TOKENS * (2 if reduced_count > 10 else 1)
            quiz = call_gemini(prompt, max_output_tokens=retry_tokens)
            quiz['question_count'] = reduced_count
            quiz['reduced_from'] = question_count
            return quiz
        raise



