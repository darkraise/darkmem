import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import {
  Home,
  Brain,
  MessageSquare,
  Share2,
  GitBranch,
  Orbit,
  Network,
  FolderGit2,
  BookOpen,
  BarChart3,
  Activity,
  Cpu,
  Settings,
} from "lucide-react"
import { SidebarLayout, TopNavLayout, StackedLayout } from "darkraise-ui/layout"
import { useLayoutStore } from "darkraise-ui/layout"
import { useAuthStore } from "@/features/auth"
import { useWebSocket } from "@/lib/websocket"
import type { NavGroup } from "darkraise-ui/layout"

const nav: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", href: "/", icon: Home },
      { label: "Memories", href: "/memories", icon: Brain },
      { label: "Chat", href: "/chat", icon: MessageSquare },
    ],
  },
  {
    label: "Visualization",
    items: [
      { label: "Knowledge Graph", href: "/graph", icon: Share2 },
      { label: "Unified Graph", href: "/unified-graph", icon: GitBranch },
      { label: "Vector Space", href: "/vectors", icon: Orbit },
      { label: "Code Graph", href: "/code-graph", icon: Network },
    ],
  },
  {
    label: "Code Intelligence",
    items: [
      { label: "Repositories", href: "/repos", icon: FolderGit2 },
      { label: "Code Wiki", href: "/code-wiki", icon: BookOpen },
    ],
  },
  {
    label: "System",
    items: [
      { label: "Analytics", href: "/analytics", icon: BarChart3 },
      { label: "Pipeline", href: "/pipeline", icon: Activity },
      { label: "LLM Config", href: "/llm", icon: Cpu },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
]

function AuthenticatedLayout() {
  useWebSocket()
  const layout = useLayoutStore((s) => s.layout)

  const Layout =
    layout === "top-nav"
      ? TopNavLayout
      : layout === "stacked"
        ? StackedLayout
        : SidebarLayout

  return (
    <Layout nav={nav}>
      <Outlet />
    </Layout>
  )
}

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/login" })
    }
  },
  component: AuthenticatedLayout,
})
