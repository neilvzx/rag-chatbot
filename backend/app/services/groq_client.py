"""
Thin client for Groq's OpenAI-compatible chat completions endpoint.
No official SDK dependency required — plain HTTPS via `requests`,
which is already a transitive dependency (fastapi/httpx stack).
"""

import requests

from app.config import settings


class GroqError(Exception):
    pass


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def generate_answer(question: str, context_chunks: list[str]) -> str:
    """
    Send a question + retrieved context chunks to Groq/Llama and return
    a grounded answer. Raises GroqError on API failure so the caller can
    turn it into a clean HTTP error rather than a raw traceback.
    """
    if not settings.groq_api_key:
        raise GroqError(
            "GROQ_API_KEY is not set -- add it to your .env file "
            "(GROQ_API_KEY=gsk_...)"
        )

    context_block = "\n\n".join(
        f"[Source {i + 1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
    )

    system_prompt = (
        "You are a document Q&A assistant. Answer the user's question using "
        "ONLY the information in the provided sources below. "
        "If the answer isn't contained in the sources, say so clearly instead "
        "of guessing. When you use information from a source, cite it inline "
        "like [Source 1], [Source 2], etc."
    )

    user_prompt = f"Sources:\n\n{context_block}\n\nQuestion: {question}"

    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(GROQ_ENDPOINT, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        raise GroqError(f"Could not reach Groq API: {e}")

    if resp.status_code != 200:
        raise GroqError(f"Groq API error ({resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise GroqError(f"Unexpected Groq response shape: {data}") from e
