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
import { JobsSettingsTab } from "@/features/settings/components/jobs-settings-tab"
import { SecurityTab } from "@/features/settings/components/security-tab"
import { MaintenanceTab } from "@/features/settings/components/maintenance-tab"
import { DistributionTab } from "@/features/settings/components/distribution-tab"

const TAB_VALUES = [
  "flags",
  "llm",
  "jobs",
  "security",
  "maintenance",
  "distribution",
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
        description="Configuration: tunables, LLM purposes, jobs, security posture, maintenance, and distribution."
      />
      <Tabs
        value={tab ?? "flags"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as SettingsTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as SettingsTab }),
            })
          }
        }}
      >
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="flags">Flags</TabsTrigger>
            <TabsTrigger value="llm">LLM</TabsTrigger>
            <TabsTrigger value="jobs">Jobs</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
            <TabsTrigger value="distribution">Distribution</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="flags" className="pt-4">
          <FlagsTab />
        </TabsContent>
        <TabsContent value="llm" className="pt-4">
          <LLMTab />
        </TabsContent>
        <TabsContent value="jobs" className="pt-4">
          <JobsSettingsTab />
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
      </Tabs>
    </div>
  )
}
