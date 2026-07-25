import { Fragment } from "react"
import { Link } from "@tanstack/react-router"
import { ChevronRight } from "lucide-react"
import { splitNavHref } from "@/providers/router-adapter"
import { usePageChrome } from "./page-chrome"

/**
 * Page identity block for the app header bar (rendered via the layout's
 * `headerSlot`): a breadcrumb row above an icon + title + description +
 * actions row. darkraise-ui's PageHeader has no icon slot and renders
 * in-content, so this is a custom component fed by the page-chrome store.
 */
export function AppPageHeader() {
  const { icon: Icon, title, description, breadcrumbs, actions } =
    usePageChrome()

  if (!title) return null

  return (
    <div className="flex min-w-0 flex-1 flex-col justify-center gap-0.5 text-left">
      {breadcrumbs.length > 0 && (
        <nav
          aria-label="Breadcrumb"
          className="dm-chrome-crumbs text-muted-foreground flex items-center gap-1 text-[11px] leading-none"
        >
          {breadcrumbs.map((crumb) => {
            const target = crumb.href ? splitNavHref(crumb.href) : null
            return (
              <Fragment key={crumb.label}>
                {target ? (
                  <Link
                    to={target.to}
                    search={target.search}
                    className="hover:text-foreground transition-colors"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span>{crumb.label}</span>
                )}
                <ChevronRight aria-hidden className="h-2.5 w-2.5 shrink-0" />
              </Fragment>
            )
          })}
          <span aria-current="page" className="text-foreground/70">
            {title}
          </span>
        </nav>
      )}
      <div className="flex min-w-0 items-center gap-2.5">
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
    </div>
  )
}
