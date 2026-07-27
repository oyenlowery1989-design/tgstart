"""Shared Jinja2 environment for all dashboard route modules."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_template_dir = str(Path(__file__).resolve().parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)


def render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    return _jinja_env.get_template(template_name).render(**context)
