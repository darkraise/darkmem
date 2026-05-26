import { createFileRoute, Outlet, redirect, useRouter } from "@tanstack/react-router"
import {
  Home, Brain, MessageSquare, Share2, GitBranch, Orbit, Network,
  FolderGit2, BookOpen, BarChart3, Activity, Cpu, Clock, Settings,
} from "lucide-react"
import {
  useLayoutStore, SidebarLayout, TopNavLayout, StackedLayout,
} from "darkraise-ui/layout"
import type { NavGroup } from "darkraise-ui/layout"
import { useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/features/auth"
import { useWebSocket } from "@/lib/websocket"

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
      { label: "Pipeline", href: "/pipeline", icon: Cpu },
      { label: "Jobs", href: "/jobs", icon: Clock },
      { label: "Reindex", href: "/reindex", icon: Activity },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
]

const AUTH_VERIFY_TTL_MS = 60_000
let _lastAuthVerifyAt = 0

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/login" })
    }
    const now = Date.now()
    if (now - _lastAuthVerifyAt < AUTH_VERIFY_TTL_MS) return
    const { checkAuth } = await import("@/lib/api")
    const ok = await checkAuth()
    if (!ok) {
      useAuthStore.getState().logout()
      throw redirect({ to: "/login" })
    }
    _lastAuthVerifyAt = now
  },
  component: AuthenticatedLayout,
})

function AuthenticatedLayout() {
  useWebSocket()
  const layout = useLayoutStore((s) => s.layout)
  const router = useRouter()
  const queryClient = useQueryClient()

  const handleLogout = async () => {
    const { logout } = await import("@/lib/api")
    await logout()
    useAuthStore.getState().logout()
    queryClient.clear()
    router.navigate({ to: "/login" })
  }

  const Shell =
    layout === "top-nav" ? TopNavLayout :
    layout === "stacked"  ? StackedLayout :
                            SidebarLayout

  return (
    <Shell
      nav={nav}
      user={{ name: "Admin", email: "" }}
      onLogout={handleLogout}
      showLayoutSwitcher
    >
      <Outlet />
    </Shell>
  )
}
