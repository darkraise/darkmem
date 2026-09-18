import { lazy, Suspense } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toEditorBlocks } from "./lib/block-mapping"
import { DEMO_PAGE, DEMO_PAGE_TITLE } from "./lib/demo-page"

const PageEditor = lazy(() => import("./page-editor").then((m) => ({ default: m.PageEditor })))

const DEMO_BLOCKS = toEditorBlocks(DEMO_PAGE).blocks

/** `/notes` in demo mode: a fixed page in a read-only editor, with no save
 *  engine and so no request. */
export function DemoNotes() {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-2xl font-semibold">{DEMO_PAGE_TITLE}</h2>
      <Suspense fallback={<Skeleton className="h-40 w-full" />}>
        <PageEditor initialBlocks={DEMO_BLOCKS} editable={false} />
      </Suspense>
    </div>
  )
}
