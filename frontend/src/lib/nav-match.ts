import { ALL_NAV_ITEMS, type NavItem } from "@/lib/nav";

/**
 * Prefix-matches the current pathname against nav items so sub-routes
 * (e.g. /sessions/login/qr) still resolve to their parent nav entry.
 * Longest URL wins, so a more specific item beats a shorter prefix.
 */
export function findActiveNavItem(pathname: string): NavItem | undefined {
  return [...ALL_NAV_ITEMS]
    .sort((a, b) => b.url.length - a.url.length)
    .find(
      (item) => pathname === item.url || pathname.startsWith(`${item.url}/`),
    );
}
