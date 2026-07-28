"""Pluggable draft-reply provider, selected by name (stored in settings.provider)."""
from typing import Callable

from . import anthropic_provider, vertex

_PROVIDERS = {
    "vertex": vertex.draft_reply,
    "anthropic": anthropic_provider.draft_reply,
}


def get_provider(name: str) -> Callable:
    try:
        return _PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown provider '{name}'. Valid options: {sorted(_PROVIDERS)}")


if __name__ == "__main__":
    assert get_provider("vertex") is vertex.draft_reply
    assert get_provider("anthropic") is anthropic_provider.draft_reply
    try:
        get_provider("nonexistent")
        assert False, "should have raised"
    except ValueError:
        pass
    print("providers/__init__.py smoke check OK")
