from __future__ import annotations

import json
import re
import textwrap
import urllib.error
import urllib.request
from io import BytesIO

from django.conf import settings

from materials.supabase import download_file

try:  # pragma: no cover - optional dependency
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - handled at runtime
    PdfReader = None  # type: ignore[misc]


class GeminiError(RuntimeError):
    """Raised when Gemini quiz generation fails."""


QUESTION_BLOCK_RE = re.compile(r'("questions"\s*:\s*\[)(.*?)(\]\s*[},])', re.S)
DEFAULT_MAX_TOKENS = 8192  


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


def chunk_text(text: str, max_chars: int = 8000) -> list[str]:
    text = textwrap.dedent(text).strip()
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def build_prompt(chunks: list[str], question_count: int) -> str:
    joined = "\n\n".join(chunks[:3])
    template = textwrap.dedent("""
        You are an AI tutor. Read the provided study material and create {question_count} high-quality multiple-choice questions.
        Each question must have exactly four answer choices, indicate the correct answer, and include a short explanation referencing the source material.
        Return STRICT JSON that matches this structure:
        {{
          "quiz_title": "string",
          "questions": [
            {{
              "prompt": "string",
              "choices": ["choice A", "choice B", "choice C", "choice D"],
              "correct_index": 0,
              "explanation": "string"
            }},
            {{
              "prompt": "string",
              "choices": ["choice A", "choice B", "choice C", "choice D"],
              "correct_index": 0,
              "explanation": "string"
            }}
          ]
        }}
        Requirements:
        - Output must be valid JSON (RFC 8259) with no markdown, comments, or trailing commas.
        - The "choices" array must contain exactly four strings; separate each element with a comma.
        - Insert a comma between question objects except after the final one.
        - Do not introduce extra sections or keys beyond the schema above.
        - Use plain Unicode characters (e.g., ?) and do not emit literal \\\\u escapes.
        """).strip()
    instructions = template.format(question_count=question_count)
    return f"{instructions}\n\nMaterial:\n{joined}"



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
              "prompt": "string",
              "choices": ["string", "string", "string", "string"],
              "correct_index": 0,
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
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_output_tokens},
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


def call_gemini(prompt: str) -> dict:
    text_output, _ = _make_gemini_request(prompt)
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


def generate_quiz(material, *, question_count: int = 5) -> dict:
    question_count = max(1, min(question_count, 10))
    text = extract_text(material)
    chunks = chunk_text(text)
    prompt = build_prompt(chunks, question_count)
    try:
        return call_gemini(prompt)
    except GeminiError as exc:
        message = str(exc)
        if 'MAX_TOKENS' in message and question_count > 5:
            reduced_count = max(5, question_count - 2)
            if reduced_count < question_count:
                prompt = build_prompt(chunks, reduced_count)
                quiz = call_gemini(prompt)
                quiz['question_count'] = reduced_count
                quiz['reduced_from'] = question_count
                return quiz
        raise



