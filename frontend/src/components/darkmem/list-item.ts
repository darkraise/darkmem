/** The one definition of what a row in a browsable list looks like.
 *
 *  Two decisions live here rather than being copied into forty components.
 *
 *  **The dashed edge is the list-item style, not a status.** It used to say
 *  "candidate" on the Facts page and nothing anywhere else, which read as a
 *  page style only because every fact in the corpus happened to be a
 *  candidate. Making it the shared item edge costs the Facts page nothing:
 *  a candidate still carries `bg-muted/15` and a VerificationBadge that spells
 *  the word, so the state has two signals and the border was the weakest.
 *
 *  **Hover is an affordance, so it is opt-in.** A row the reader cannot act on
 *  must not light up under the pointer — that promises a click that does
 *  nothing. Pass `interactive` only where the row navigates or selects.
 */
import { cn } from "darkraise-ui/lib"

export function listItemClass({
  interactive = false,
  className,
}: {
  interactive?: boolean
  className?: string
} = {}) {
  return cn(
    "border-border rounded-md border border-dashed transition-colors",
    interactive &&
      "hover:border-primary/40 hover:bg-muted/40 focus-within:border-primary/40",
    className,
  )
}
