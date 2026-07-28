"""Anthropic (Claude) provider. Requires ANTHROPIC_API_KEY in .env. Model name comes from
the 'model' setting, falling back to BOT_REPLY_ANTHROPIC_MODEL, falling back to a safe
default."""
import os
from typing import List

import anthropic


def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


async def draft_reply(system_prompt: str, history: List[dict], incoming: str, model: str = None) -> str:
    model_name = model or os.getenv("BOT_REPLY_ANTHROPIC_MODEL", "claude-sonnet-5")
    client = _client()
    messages = [{"role": "user", "content": f"{h['sender']}: {h['text']}"} for h in history]
    messages.append({"role": "user", "content": incoming})
    response = await client.messages.create(
        model=model_name, max_tokens=1024, system=system_prompt, messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(draft_reply)
    sig = inspect.signature(draft_reply)
    assert list(sig.parameters.keys())[:3] == ["system_prompt", "history", "incoming"]
    print("anthropic_provider.py smoke check OK (signature only — no live API call)")
