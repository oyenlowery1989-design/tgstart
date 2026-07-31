const NAV_GROUPS = [
  {
    label: "Accounts",
    items: [{ label: "Sessions", href: "/sessions", external: true }],
  },
  {
    label: "Data",
    items: [
      { label: "Chats", href: "/chats", external: true },
      { label: "Groups", href: "/groups", external: true },
      { label: "Scrape", href: "/scrape", external: true },
      { label: "Stats", href: "/app/stats", external: false },
    ],
  },
  {
    label: "Automation",
    items: [
      { label: "Ghost Mirror", href: "/ghost", external: true },
      { label: "Bot Reply", href: "/reply", external: true },
    ],
  },
];

export default function Sidebar() {
  const currentPath = window.location.pathname;
  return (
    <nav className="w-56 shrink-0 bg-slate-900 border-r border-slate-800 min-h-screen px-3 py-4">
      <div className="text-slate-200 font-semibold text-lg px-2 mb-6">
        Telegram Suite
      </div>
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-5">
          <div className="text-slate-500 text-xs uppercase tracking-wide px-2 mb-2">
            {group.label}
          </div>
          {group.items.map((item) => {
            const active = !item.external && currentPath === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                className={
                  "block px-2 py-1.5 rounded text-sm mb-0.5 " +
                  (active
                    ? "bg-slate-800 text-slate-50 border-l-2 border-blue-400 -ml-px pl-2"
                    : "text-slate-300 hover:bg-slate-800 hover:text-slate-50")
                }
              >
                {item.label}
              </a>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
