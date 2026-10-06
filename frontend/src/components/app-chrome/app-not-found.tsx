import { Link } from "@tanstack/react-router"
import { FileQuestion } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
import { PageChrome } from "./page-chrome"

/**
 * The one not-found page a signed-in reader sees, inside the app shell, for
 * any path no route serves: an unknown top-level path (`/does-not-exist`)
 * and an unknown path under a real page (`/settings/foo/bar`) alike. The
 * header names it, and no nav item claims it (see `useIsNotFound`).
 */
export function AppNotFound() {
  return (
    <>
      <PageChrome icon={FileQuestion} title="Page not found" />
      <EmptyState
        kind="missing"
        scope="page"
        title="Page not found"
        description="Nothing lives at this address. It may have moved, or the link may be mistyped."
        action={
          <Button asChild>
            <Link to="/">Back to the dashboard</Link>
          </Button>
        }
      />
    </>
  )
}
