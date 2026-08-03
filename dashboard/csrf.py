"""CSRF protection: double-submit cookie, checked via header (JSON/fetch
routes) or hidden form field (native <form> posts).

HTTP Basic auth alone doesn't stop CSRF: browsers replay cached Basic-auth
credentials on cross-origin requests, so a malicious page could still
trigger a mutating POST while the dashboard tab is authenticated. The
cookie is set on every response (see `ensure_cookie_middleware` in app.py);
callers must echo it back via the `X-CSRF-Token` header (fetch) or a
`csrf_token` form field (native forms) to prove the request originated
same-origin.
"""
import secrets

from fastapi import Form, HTTPException, Request

COOKIE_NAME = "csrf_token"
HEADER_NAME = "x-csrf-token"


def new_token() -> str:
    return secrets.token_urlsafe(32)


def require_csrf_header(request: Request) -> None:
    cookie_token = request.cookies.get(COOKIE_NAME)
    header_token = request.headers.get(HEADER_NAME)
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(403, "Missing or invalid CSRF token")


def require_csrf_form(request: Request, csrf_token: str = Form(...)) -> None:
    cookie_token = request.cookies.get(COOKIE_NAME)
    if not cookie_token or not secrets.compare_digest(cookie_token, csrf_token):
        raise HTTPException(403, "Missing or invalid CSRF token")


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(require_csrf_header) is False
    assert len(new_token()) > 20
    print("csrf.py smoke check OK")
