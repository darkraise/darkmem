import { createFileRoute } from "@tanstack/react-router"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { Settings } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { FlagsTab } from "@/features/settings/components/flags-tab"
import { LLMTab } from "@/features/settings/components/llm-tab"
import { SecurityTab } from "@/features/settings/components/security-tab"
import { MaintenanceTab } from "@/features/settings/components/maintenance-tab"
import { DistributionTab } from "@/features/settings/components/distribution-tab"
import { ResearchTab } from "@/features/settings/components/research-tab"

const TAB_VALUES = [
  "flags",
  "llm",
  "security",
  "maintenance",
  "distribution",
  "research",
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
      <PageChrome
        icon={Settings}
        title="Settings"
        description="Configuration: tunables, LLM purposes, security posture, maintenance, and distribution."
      />
      <Tabs
        border="default"
        value={tab ?? "flags"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as SettingsTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as SettingsTab }),
            })
          }
        }}
      >
        {/* Full-width strip with equal-width items: `w-full` on the list and
            `flex-1` on each trigger, so the tabs divide the content area
            evenly instead of hugging their labels. The scroll container stays
            for narrow viewports, where seven equal columns still overflow. */}
        <div className="overflow-x-auto">
          <TabsList className="w-full">
            <TabsTrigger className="flex-1" value="flags">Flags</TabsTrigger>
            <TabsTrigger className="flex-1" value="llm">LLM</TabsTrigger>
            <TabsTrigger className="flex-1" value="security">Security</TabsTrigger>
            <TabsTrigger className="flex-1" value="maintenance">Maintenance</TabsTrigger>
            <TabsTrigger className="flex-1" value="distribution">Distribution</TabsTrigger>
            <TabsTrigger className="flex-1" value="research">Research</TabsTrigger>
          </TabsList>
        </div>
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
        <TabsContent value="distribution" className="pt-4">
          <DistributionTab />
        </TabsContent>
        <TabsContent value="research" className="pt-4">
          <ResearchTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
