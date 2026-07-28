"""Vertex Gemini provider. Requires GOOGLE_APPLICATION_CREDENTIALS (service account JSON
path), GCP_PROJECT_ID, and GCP_LOCATION in .env. Model name comes from the 'model' setting,
falling back to BOT_REPLY_VERTEX_MODEL, falling back to a safe default."""
import os
from typing import List

from google import genai


def _client() -> genai.Client:
    project = os.getenv("GCP_PROJECT_ID", "")
    location = os.getenv("GCP_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project, location=location)


async def draft_reply(system_prompt: str, history: List[dict], incoming: str, model: str = None) -> str:
    model_name = model or os.getenv("BOT_REPLY_VERTEX_MODEL", "gemini-2.0-flash-001")
    client = _client()
    history_text = "\n".join(f"{h['sender']}: {h['text']}" for h in history)
    prompt = f"{system_prompt}\n\nRecent conversation:\n{history_text}\n\nNew message:\n{incoming}\n\nReply:"
    response = await client.aio.models.generate_content(model=model_name, contents=prompt)
    return (response.text or "").strip()


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(draft_reply)
    sig = inspect.signature(draft_reply)
    assert list(sig.parameters.keys())[:3] == ["system_prompt", "history", "incoming"]
    print("vertex.py smoke check OK (signature only — no live API call)")
