import { createFileRoute } from "@tanstack/react-router"
import { Tabs, TabsContent, TabsTrigger } from "darkraise-ui/components/tabs"
import {
  Bot,
  Flag,
  KeyRound,
  Palette,
  Plug,
  Search,
  HardDriveDownload,
  Bell,
  Settings,
  ShieldCheck,
  Wrench,
} from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { ScrollTabsList } from "@/components/darkmem"
import {
  AppearanceTab,
  GraphAppearanceCard,
} from "@/features/settings/components/appearance-tab"
import { FlagsTab } from "@/features/settings/components/flags-tab"
import { GitAccountsTab } from "@/features/settings/components/git-accounts-tab"
import { LLMTab } from "@/features/settings/components/llm-tab"
import { SecurityTab } from "@/features/settings/components/security-tab"
import { MaintenanceTab } from "@/features/settings/components/maintenance-tab"
import { DistributionTab } from "@/features/settings/components/distribution-tab"
import { ResearchTab } from "@/features/settings/components/research-tab"
import { BackupsTab } from "@/features/settings/components/backups-tab"
import { NotificationsTab } from "@/features/settings/components/notifications-tab"

export const TAB_VALUES = [
  "flags",
  "llm",
  "security",
  "maintenance",
  "integration",
  "git-accounts",
  "research",
  "notifications",
  "backups",
  "appearance",
] as const
export type SettingsTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/settings")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as SettingsTab)
      ? (search.tab as SettingsTab)
      : undefined,
  }),
  component: SettingsPage,
})

function SettingsPage() {
  const { tab } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <div className="space-y-4">
      <PageChrome icon={Settings} title="Settings" />
      <Tabs
        border="accent"
        value={tab ?? "flags"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as SettingsTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as SettingsTab }),
            })
          }
        }}
      >
        {/* The strip stays put while the tab body scrolls.

            `sticky` is on this wrapper and the scroller (`ScrollTabsList`)
            inside it, because they cannot be the same element: a scroll
            container clips its own overflow, which would cut off the
            background extension below, and a sticky element *inside* a scroll
            container pins to that container rather than to the page.

            The extension exists because sticky pins the strip to the
            scrollport's content edge, leaving the shell's top padding as a
            band that scrolling rows still show through. `bottom-full` paints
            the same background upward across it; the height only has to
            exceed that padding, since `main`'s own overflow clips whatever
            reaches past it — which is what keeps this off the shell's
            density-dependent padding value.

            No horizontal bleed is needed for the same clipping reason in
            reverse: content sits inside `main`'s content box and cannot paint
            into the side gutters, so a strip spanning the content width
            already covers everything that passes under it. */}
        <div className="bg-background before:bg-background sticky top-0 z-20 pb-2 before:absolute before:inset-x-0 before:bottom-full before:h-8 before:content-['']">
          <ScrollTabsList activeValue={tab ?? "flags"} scrollButtons>
            <TabsTrigger className="flex-1 gap-2" value="flags">
              <Flag aria-hidden className="size-[var(--icon-size)]" />
              Flags
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="llm">
              <Bot aria-hidden className="size-[var(--icon-size)]" />
              LLM
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="security">
              <ShieldCheck aria-hidden className="size-[var(--icon-size)]" />
              Security
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="maintenance">
              <Wrench aria-hidden className="size-[var(--icon-size)]" />
              Maintenance
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="integration">
              <Plug aria-hidden className="size-[var(--icon-size)]" />
              Integration
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="git-accounts">
              <KeyRound aria-hidden className="size-[var(--icon-size)]" />
              Git accounts
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="notifications">
              <Bell aria-hidden className="size-[var(--icon-size)]" />
              Notifications
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="research">
              <Search aria-hidden className="size-[var(--icon-size)]" />
              Research
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="backups">
              <HardDriveDownload
                aria-hidden
                className="size-[var(--icon-size)]"
              />
              Backups
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="appearance">
              <Palette aria-hidden className="size-[var(--icon-size)]" />
              Appearance
            </TabsTrigger>
          </ScrollTabsList>
        </div>
        <TabsContent value="git-accounts" className="pt-4">
          <GitAccountsTab />
        </TabsContent>
        <TabsContent value="flags" className="pt-4">
          <FlagsTab />
        </TabsContent>
        <TabsContent value="llm" className="pt-4">
          <LLMTab />
        </TabsContent>
        <TabsContent value="security" className="pt-4">
          <SecurityTab />
        </TabsContent>
        <TabsContent value="maintenance" className="pt-4">
          <MaintenanceTab />
        </TabsContent>
        <TabsContent value="integration" className="pt-4">
          <DistributionTab />
        </TabsContent>
        <TabsContent value="notifications" className="pt-4">
          <NotificationsTab />
        </TabsContent>
        <TabsContent value="research" className="pt-4">
          <ResearchTab />
        </TabsContent>
        <TabsContent value="backups" className="pt-4">
          <BackupsTab />
        </TabsContent>
        <TabsContent value="appearance" className="space-y-4 pt-4">
          <AppearanceTab />
          <GraphAppearanceCard />
        </TabsContent>
      </Tabs>
    </div>
  )
}
