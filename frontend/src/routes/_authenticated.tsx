import {
  createFileRoute,
  Outlet,
  redirect,
  useRouter,
  useRouterState,
} from "@tanstack/react-router"
import {
  Activity,
  DollarSign,
  Timer,
  BookOpen,
  Brain,
  ClipboardCheck,
  FileText,
  FolderKanban,
  FolderGit2,
  LayoutDashboard,
  MessageSquare,
  Network,
  NotebookPen,
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
import { cn } from "darkraise-ui/lib"
import { UiLabelsProvider } from "darkraise-ui/labels"
import { useState } from "react"
import { ChangePasswordDialog } from "@/features/settings/components/change-password-dialog"
import { useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/features/auth"
import { useWebSocket } from "@/lib/websocket"
import { DEMO } from "@/lib/demo-flag"
import {
  AppPageHeader,
  BackToTop,
  HeaderControls,
  ProjectScopeReconciler,
} from "@/components/app-chrome"
import { projectScopeDisabledReason } from "@/components/app-chrome/project-switcher"

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
    label: "Projects",
    items: [
      { label: "Projects", href: "/projects", icon: FolderKanban },
      // /documents shipped with TH1.16 and had no nav entry at all, so the
      // surface existed and was unreachable. This closes that for both.
      { label: "Documents", href: "/documents", icon: FileText },
      { label: "Notes", href: "/notes", icon: NotebookPen },
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
      { label: "Usage", href: "/usage", icon: DollarSign },
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

/** Routes whose content is a canvas rather than a document, and so keeps the
 *  full width of the viewport. */
const FULL_BLEED_ROUTES = ["/memory-graph", "/code/graph"] as const

/** Routes that fill the scrollport instead of growing with their content, so
 *  the page's own panes scroll rather than the page. `h-full` resolves here
 *  because the library's `.dr-sidebar-layout-content` is a `flex-1` child of a
 *  fixed-height column — which is why this beats a `calc(100vh - Nrem)` guess
 *  that the theme's density axis would invalidate.
 *
 *  Every FULL_BLEED_ROUTE is implicitly one of these and does not need listing:
 *  a canvas page measures its own container with a ResizeObserver and mounts
 *  the renderer only once that container reports a non-zero box. Without a
 *  definite height on `main` the page root's `h-full` resolves against an
 *  auto-height parent, the absolutely-positioned canvas layer collapses to 0,
 *  and the observer never fires — so the graph renders nothing, with no error
 *  and an empty-looking page. That stayed invisible while those pages had no
 *  data to draw, because the empty state carries its own height. */
export const FULL_HEIGHT_ROUTES = [
  "/chat",
  "/projects/",
  "/documents",
  "/notes",
] as const

/** Routes that drop the reading-width cap without being a pan/zoom canvas.
 *  Chat is one: its three panes are resizable, so every capped pixel is width
 *  the reader cannot give to the conversation or the retrieval context. A
 *  project workspace (`/projects/<name>`, trailing slash so the `/projects`
 *  index card grid stays capped) is the other: its tree/reader split is
 *  resizable the same way, and `/documents` mounts that same workspace with a
 *  project switcher -- and `/notes` is its own tree/pane split over the
 *  personal space's pages, so it is here for exactly that argument and no
 *  other.
 *  Kept separate from FULL_BLEED_ROUTES because that
 *  list also means "measures its own container", which is a claim about the
 *  canvas pages and not about either of these. */
export const FULL_WIDTH_ROUTES = [
  "/chat",
  "/projects/",
  "/documents",
  "/notes",
] as const

function AuthenticatedLayout() {
  const layout = useLayoutStore((s) => s.layout)
  const router = useRouter()
  const queryClient = useQueryClient()
  const [changingPassword, setChangingPassword] = useState(false)
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  // Content is capped on wide viewports so a dense page does not stretch a
  // card row to 2000px and leave the eye travelling between a label on the
  // left and its value on the right. The graph pages opt out: they render a
  // pan/zoom canvas whose usable area IS the viewport, so a cap there is lost
  // working space rather than restored legibility.
  const fullBleed = FULL_BLEED_ROUTES.some((route) =>
    pathname.startsWith(route),
  )
  const fullHeight =
    fullBleed || FULL_HEIGHT_ROUTES.some((route) => pathname.startsWith(route))
  const fullWidth =
    fullBleed || FULL_WIDTH_ROUTES.some((route) => pathname.startsWith(route))

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
    // Renames the UserMenu's profile slot. The library fixes its three item
    // labels in `useUiLabels`, and `UiLabelsProvider` is the sanctioned way to
    // override one — cheaper and less brittle than reimplementing the menu to
    // add a fourth item. This app has no profile, so the slot is free.
    <UiLabelsProvider value={{ userMenu: { profile: "Change password" } }}>
      <Shell
        nav={nav}
        // Controlled, not `defaultActiveBar`: this app ships no
        // `showActiveBarToggle`, so nothing can change the indicator and
        // "pinned" is the honest spelling. Ignored by the two sidebar-less
        // layouts. Requires darkraise-ui >= 6.2.0.
        activeBar="both"
        // Off in favour of `MinimalThemeSwitcher` below. The shell's own
        // switcher renders every axis in `themeConfig.switcher.axes`, and all
        // of them are on so Settings -> Appearance can offer the full panel;
        // the header wants three. See `minimal-theme-switcher.tsx` for the
        // library gap that forces the split.
        showThemeSwitcher={false}
        headerSlot={
          <>
            <AppPageHeader />
            <HeaderControls
              projectDisabledReason={projectScopeDisabledReason(pathname)}
            />
          </>
        }
        user={{ name: DEMO ? "Demo" : "Admin", email: "" }}
        // The library's UserMenu has three fixed slots — profile, settings,
        // logout — with no arbitrary-item API, so the account action rides the
        // profile slot and `UiLabelsProvider` below renames it. Omitted in demo
        // mode: there is no backend to change a password on, and an item that
        // cannot work should not be in the menu.
        onProfile={DEMO ? undefined : () => setChangingPassword(true)}
        onLogout={handleLogout}
      >
        {!DEMO && <LiveUpdates />}
        <ProjectScopeReconciler />
        <main
          className={cn(
            "w-full",
            !fullWidth && "mx-auto max-w-[1400px]",
            fullHeight && "h-full",
          )}
        >
          <Outlet />
        </main>
        <BackToTop />
        {!DEMO && (
          <ChangePasswordDialog
            open={changingPassword}
            onOpenChange={setChangingPassword}
          />
        )}
      </Shell>
    </UiLabelsProvider>
  )
}
