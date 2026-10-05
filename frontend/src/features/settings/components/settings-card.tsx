import type { ReactNode } from "react"
import type { LucideIcon } from "lucide-react"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"

/** The one card treatment every Settings tab uses.
 *
 *  A library `Card` with the Flags tab's header: icon, mono uppercase title,
 *  optional help tip, then whatever `actions` the card offers, right-aligned.
 *  Settings had four header styles (mono uppercase, sentence-case bold, a
 *  26px library CardTitle and a ModuleSurface strip) across one page, so the
 *  same kind of card read as a different kind of thing on every tab.
 *
 *  `flex-row space-y-0` override the library's `.dr-card-header`, which is
 *  `flex flex-col space-y-1`; without them the header stacks in a column. */
export function SettingsCard({
  icon: Icon,
  title,
  help,
  actions,
  className,
  contentClassName,
  children,
}: {
  icon: LucideIcon
  title: string
  help?: ReactNode
  actions?: ReactNode
  className?: string
  contentClassName?: string
  children: ReactNode
}) {
  return (
    <Card className={cn("gap-0 py-0", className)}>
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 overflow-hidden border-b px-4 py-2.5">
        <Icon aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="text-foreground min-w-0 font-mono text-xs font-semibold tracking-[0.14em] uppercase sm:truncate">
          {title}
        </h3>
        {help && (
          <span className="shrink-0">
            <HelpTip label={`About ${title}`}>{help}</HelpTip>
          </span>
        )}
        {actions && (
          <div className="ml-auto flex shrink-0 items-center gap-2">
            {actions}
          </div>
        )}
      </CardHeader>
      <CardContent
        className={cn("flex flex-col gap-2.5 p-4", contentClassName)}
      >
        {children}
      </CardContent>
    </Card>
  )
}
