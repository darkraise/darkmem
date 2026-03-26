import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Overview", icon: "⊞" },
  { to: "/memories", label: "Memories", icon: "◉" },
  { to: "/graph", label: "Knowledge Graph", icon: "◎" },
  { to: "/vectors", label: "Vector Space", icon: "◈" },
  { to: "/search", label: "Search", icon: "⊕" },
  null,
  { to: "/analytics", label: "Analytics", icon: "▤" },
  { to: "/keys", label: "API Keys", icon: "⊡" },
  { to: "/llm", label: "LLM Config", icon: "⊙" },
  { to: "/settings", label: "Settings", icon: "⊛" },
] as const satisfies (null | { to: string; label: string; icon: string })[];

export function Sidebar() {
  return (
    <aside className="w-56 bg-card border-r border-border flex flex-col shrink-0">
      <div className="p-4 border-b border-border">
        <span className="text-lg font-bold font-mono text-foreground">darkmem</span>
      </div>
      <nav className="flex-1 py-2">
        {navItems.map((item, i) =>
          item === null ? (
            <div key={i} className="border-t border-border my-2" />
          ) : (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
                  isActive
                    ? "text-primary bg-accent border-l-2 border-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          )
        )}
      </nav>
    </aside>
  );
}
