import {
  createFileRoute,
  Outlet,
  redirect,
  useRouter,
} from "@tanstack/react-router"
import {
  Activity,
  Brain,
  Code2,
  LayoutDashboard,
  Library,
  MessageSquare,
  Settings,
  Waypoints,
} from "lucide-react"
import {
  useBrandStore,
  useLayoutStore,
  SidebarLayout,
  TopNavLayout,
  StackedLayout,
} from "darkraise-ui/layout"
import type { NavGroup } from "darkraise-ui/layout"
import { useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/features/auth"
import { useWebSocket } from "@/lib/websocket"
import { DEMO } from "@/demo/flag"
import { DetailLevelToggle } from "@/components/darkmem"

const nav: NavGroup[] = [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Memories", href: "/memories", icon: Brain },
      { label: "Knowledge", href: "/knowledge", icon: Library },
      { label: "Chat", href: "/chat", icon: MessageSquare },
    ],
  },
  {
    label: "Explore",
    items: [
      { label: "Code", href: "/code", icon: Code2 },
      { label: "Memory Graph", href: "/memory-graph", icon: Waypoints },
    ],
  },
  {
    label: "Operate",
    items: [
      { label: "Activity", href: "/activity", icon: Activity },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
]

useBrandStore.setState({ appName: "darkmem" })

const AUTH_VERIFY_TTL_MS = 60_000
let _lastAuthVerifyAt = 0

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async () => {
    if (DEMO) return
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

function LiveUpdates() {
  useWebSocket()
  return null
}

function AuthenticatedLayout() {
  const layout = useLayoutStore((s) => s.layout)
  const router = useRouter()
  const queryClient = useQueryClient()

  const handleLogout = async () => {
    if (!DEMO) {
      const { logout } = await import("@/lib/api")
      await logout()
      useAuthStore.getState().logout()
    }
    queryClient.clear()
    router.navigate({ to: "/login" })
  }

  const Shell =
    layout === "top-nav"
      ? TopNavLayout
      : layout === "stacked"
        ? StackedLayout
        : SidebarLayout

  return (
    <Shell
      nav={nav}
      headerSlot={<DetailLevelToggle />}
      user={{ name: DEMO ? "Demo" : "Admin", email: "" }}
      onLogout={handleLogout}
    >
      {!DEMO && <LiveUpdates />}
      <Outlet />
    </Shell>
  )
}
