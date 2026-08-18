import {
  createFileRoute,
  Outlet,
  redirect,
  useRouter,
} from "@tanstack/react-router"
import {
  Activity,
  Timer,
  BookOpen,
  Brain,
  ClipboardCheck,
  FileText,
  FolderGit2,
  LayoutDashboard,
  MessageSquare,
  Network,
  ScrollText,
  Settings,
  Tags,
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
import { DEMO } from "@/lib/demo-flag"
import { DetailLevelToggle } from "@/components/darkmem"
import {
  AppPageHeader,
  BackToTop,
  ContextChip,
  ProjectSwitcher,
} from "@/components/app-chrome"

const nav: NavGroup[] = [
  {
    items: [{ label: "Dashboard", href: "/", icon: LayoutDashboard }],
  },
  {
    label: "Memories",
    items: [
      { label: "Memories", href: "/memories", icon: Brain },
      { label: "Memory Graph", href: "/memory-graph", icon: Waypoints },
    ],
  },
  {
    label: "Knowledge",
    items: [
      { label: "Facts", href: "/knowledge/facts", icon: ScrollText },
      // L3 has no live channel until article synthesis ships behind G-D; the
      // route stays reachable and honest, but nothing advertises an empty layer.
      ...(DEMO
        ? [{ label: "Articles", href: "/knowledge/articles", icon: FileText }]
        : []),
      { label: "Topics", href: "/knowledge/topics", icon: Tags },
      { label: "Review", href: "/knowledge/review", icon: ClipboardCheck },
    ],
  },
  {
    label: "Code",
    items: [
      { label: "Repositories", href: "/code/repositories", icon: FolderGit2 },
      { label: "Code Graph", href: "/code/graph", icon: Network },
      { label: "Code Wiki", href: "/code/wiki", icon: BookOpen },
    ],
  },
  {
    label: "Operate",
    items: [
      { label: "Chat", href: "/chat", icon: MessageSquare },
      { label: "Jobs", href: "/jobs", icon: Timer },
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
      // Controlled, not `defaultActiveBar`: this app ships no
      // `showActiveBarToggle`, so nothing can change the indicator and
      // "pinned" is the honest spelling. Ignored by the two sidebar-less
      // layouts. Requires darkraise-ui >= 6.2.0.
      activeBar="both"
      headerSlot={
        <>
          <AppPageHeader />
          <ProjectSwitcher />
          <ContextChip />
          <DetailLevelToggle />
        </>
      }
      user={{ name: DEMO ? "Demo" : "Admin", email: "" }}
      onLogout={handleLogout}
    >
      {!DEMO && <LiveUpdates />}
      <Outlet />
      <BackToTop />
    </Shell>
  )
}
