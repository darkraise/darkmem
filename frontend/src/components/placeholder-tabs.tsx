import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { EmptyState } from "@/components/darkmem"

export interface PlaceholderTab {
  value: string
  label: string
  /** The page's own mark, as a component — EmptyState renders it. */
  icon: LucideIcon
  title: string
  description: ReactNode
  action?: ReactNode
}

export function PlaceholderTabs({
  tabs,
  defaultValue,
}: {
  tabs: PlaceholderTab[]
  defaultValue?: string
}) {
  return (
    <Tabs defaultValue={defaultValue ?? tabs[0]?.value}>
      <div className="overflow-x-auto">
        <TabsList>
          {tabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      {tabs.map((tab) => (
        <TabsContent key={tab.value} value={tab.value} className="pt-4">
          <EmptyState
            kind="empty"
            icon={tab.icon}
            title={tab.title}
            description={tab.description}
            action={tab.action}
          />
        </TabsContent>
      ))}
    </Tabs>
  )
}
