import { Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { splitNavHref } from "@/providers/router-adapter"
import { usePageChrome } from "./page-chrome"

/**
 * Page identity block for the app header bar (rendered via the layout's
 * `headerSlot`): an optional back button, then icon + title + description +
 * actions. darkraise-ui's PageHeader has no icon slot and renders
 * in-content, so this is a custom component fed by the page-chrome store.
 *
 * The back button is icon-only and names its destination in a tooltip. It
 * used to render the label as text beside the arrow, which the top-nav
 * layout then hid in CSS -- so that layout already showed a bare arrow with
 * nothing anywhere saying where it went. One treatment everywhere, and the
 * destination is always reachable.
 */
export function AppPageHeader() {
  const { icon: Icon, title, description, parent, actions } = usePageChrome()

  if (!title) return null

  const back = parent ? splitNavHref(parent.href) : null

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2.5 text-left">
      {parent && back && (
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                asChild
                className="text-muted-foreground hover:text-foreground -ml-1 shrink-0"
              >
                <Link
                  to={back.to}
                  search={back.search}
                  aria-label={`Back to ${parent.label}`}
                >
                  <ArrowLeft aria-hidden className="size-4" />
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Back to {parent.label}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
      {Icon && (
        <span className="bg-primary/10 text-primary flex h-7 w-7 shrink-0 items-center justify-center rounded-md">
          <Icon aria-hidden className="h-4 w-4" />
        </span>
      )}
      <h1 className="shrink-0 text-sm font-semibold">{title}</h1>
      {description && (
        <p className="dm-chrome-desc text-muted-foreground border-border hidden min-w-0 truncate border-l pl-2.5 text-sm lg:block">
          {description}
        </p>
      )}
      {actions && (
        <div className="ml-auto flex shrink-0 items-center gap-2 pl-2">
          {actions}
        </div>
      )}
    </div>
  )
}
