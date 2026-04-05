import { NavLink } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  LayoutDashboard,
  Brain,
  Network,
  Hexagon,
  Atom,
  BarChart3,
  Cpu,
  Activity,
  Settings,
  LogOut,
  MessageCircle,
  GitBranch,
  GitGraph,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const navItems: (NavItem | null)[] = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/memories", label: "Memories", icon: Brain },
  { to: "/graph", label: "Knowledge Graph", icon: Network },
  { to: "/unified-graph", label: "Unified Graph", icon: Hexagon },
  { to: "/vectors", label: "Vector Space", icon: Atom },
  { to: "/chat", label: "Chat", icon: MessageCircle },
  { to: "/repos", label: "Repositories", icon: GitBranch },
  { to: "/code-graph", label: "Code Graph", icon: GitGraph },
  null,
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/llm", label: "LLM Config", icon: Cpu },
  { to: "/pipeline", label: "Pipeline", icon: Activity },
  { to: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  onLogout: () => void;
}

export function Sidebar({ onLogout }: SidebarProps) {
  return (
    <aside className="w-56 shrink-0 bg-card border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <span className="text-lg font-bold font-mono text-foreground">darkmem</span>
      </div>
      <nav className="flex-1 py-2">
        {navItems.map((item, i) =>
          item === null ? (
            <Separator key={i} className="my-2" />
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
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          )
        )}
      </nav>
      <div className="border-t border-border p-2">
        <Button
          variant="ghost"
          onClick={onLogout}
          className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
