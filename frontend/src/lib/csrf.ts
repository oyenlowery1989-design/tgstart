// Shared across pages (unlike the page-scoped `lib/<page>-api.ts` convention):
// CSRF is cross-cutting infra, not page business logic. The backend sets a
// `csrf_token` cookie on every response (see dashboard/csrf.py); every
// mutating fetch must echo it back via this header for the request to be
// accepted.

export function csrfToken(): string {
  return document.cookie.match(/(?:^|; )csrf_token=([^;]*)/)?.[1] ?? "";
}
