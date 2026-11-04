import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Check, Copy, KeyRound } from "lucide-react"
import {
  Clipboard,
  ClipboardIndicator,
  ClipboardTrigger,
} from "darkraise-ui/components/clipboard"
import { useCreateApiKey, type ApiKeyCreated } from "@/hooks/api"
import { McpConnectSnippets } from "./mcp-connect-snippets"

/** What a key is allowed to do, in the words of someone who has to choose.
 *
 *  The scope literals are the API's closed set and must match
 *  `app/services/api_key_scopes.py`; the labels are the whole point of this
 *  screen being a picker rather than a text box. The old field was free text
 *  split on commas, so `raed` was a valid thing to type and the failure
 *  arrived from the server after the click.
 *
 *  Checkbox rows rather than a MultiSelect: there are only three, every one
 *  is visible without opening anything, and the MultiSelect's listbox
 *  rendered inside the dialog's scroll box, so `admin` sat below its bottom
 *  edge where nobody saw it.
 *
 *  `ratify` is deliberately not here. It is not a scope at all — confirming a
 *  fact stays a human action.
 */
/** Short tag for the key list, full wording for the picker. One table, so
 *  the list and the picker cannot describe a scope two ways. */
export const SCOPE_LABELS: Record<string, { short: string; full: string }> = {
  // `capture` is every MCP write that is not `admin`: memory add, update and
  // delete, document filing, editing and deletion, document block edits,
  // work-log appends and research filings. "Save new memories" read as
  // append-only.
  capture: {
    short: "Write",
    full: "Add, edit and delete memories, documents and work-log entries",
  },
  read: {
    short: "Read",
    full: "Search and read memories, documents, facts and code",
  },
  // `admin` covers unrelated powers and the label has to carry all of them:
  // the push webhook, which is the ordinary reason to mint one of these
  // keys, the file-scoped reindex, and on /mcp `document_delete_subtree` and
  // `worklog_purge` -- which erase with no undo. Naming only the erase leaves
  // a webhook operator hunting for a narrower scope that does not exist;
  // naming only the webhook understates what a leak costs.
  admin: {
    short: "Admin",
    full: "Receive push updates, reindex repositories, delete document subtrees, purge work logs",
  },
}

const SCOPE_ITEMS = (["capture", "read", "admin"] as const).map((value) => ({
  value,
  label: SCOPE_LABELS[value]!.full,
}))

/**
 * Creating a key, in a dialog rather than inline on the card.
 *
 * The secret is shown ONCE, on the create response, and no read surface can
 * hand it back. Inline on the card it appeared below a form the reader had
 * usually scrolled past by the time it rendered. Here it replaces the form in
 * a box that will not close until dismissed, which is the only moment the
 * credential exists: once a key is shown, Escape and a click outside do
 * nothing, and only "I have copied it" closes it.
 */
export function ApiKeyDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const createKey = useCreateApiKey()
  const [label, setLabel] = useState("")
  const [scopes, setScopes] = useState<string[]>(["read"])
  const [issued, setIssued] = useState<ApiKeyCreated | null>(null)

  function close(next: boolean) {
    onOpenChange(next)
    if (!next) {
      // Reset on the way out, not the way in: the secret must not survive a
      // reopen, and a half-typed label should not either.
      setLabel("")
      setScopes(["read"])
      setIssued(null)
      createKey.reset()
    }
  }

  return (
    // Once a key is on screen a stray Escape or outside click must not lose
    // it, but the X is a deliberate dismissal like "I have copied it": a close
    // button that does nothing reads as broken.
    <Dialog
      open={open}
      onOpenChange={close}
      closeOnEscape={!issued}
      closeOnOutsidePointerDown={!issued}
    >
      <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col gap-3 overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{issued ? "Your new key" : "New key"}</DialogTitle>
          <DialogDescription>
            {issued
              ? "Copy it now. For your security it is never shown again."
              : "A key lets an app or an AI agent use darkmem without logging in."}
          </DialogDescription>
        </DialogHeader>

        {issued ? (
          <>
            <div className="border-inset bg-muted/20 flex items-start gap-2 rounded-md border border-dashed p-2.5">
              <code className="min-w-0 flex-1 font-mono text-sm break-all">
                {issued.token}
              </code>
              <Clipboard value={issued.token} toast>
                <ClipboardTrigger aria-label="Copy key">
                  <ClipboardIndicator
                    copied={<Check className="size-4" />}
                    fallback={<Copy className="size-4" />}
                  />
                </ClipboardTrigger>
              </Clipboard>
            </div>
            <p className="text-muted-foreground text-sm">
              To connect an MCP client with this key:
            </p>
            <McpConnectSnippets apiKey={issued.token} />
            <DialogFooter>
              <Button onClick={() => close(false)}>I have copied it</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              <Label
                htmlFor="apikey-label"
                className="text-muted-foreground text-sm"
              >
                What is this key for?
              </Label>
              <Input
                id="apikey-label"
                placeholder="e.g. my laptop's assistant"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>

            <fieldset className="flex flex-col gap-1.5">
              <legend className="text-muted-foreground mb-1 text-sm">
                What may it do?
              </legend>
              {SCOPE_ITEMS.map((item) => (
                <div key={item.value} className="flex items-start gap-2">
                  <Checkbox
                    id={`apikey-scope-${item.value}`}
                    className="mt-0.5"
                    checked={scopes.includes(item.value)}
                    onCheckedChange={(checked) =>
                      setScopes((prev) =>
                        checked === true
                          ? SCOPE_ITEMS.map((i) => i.value).filter(
                              (v) => v === item.value || prev.includes(v),
                            )
                          : prev.filter((v) => v !== item.value),
                      )
                    }
                  />
                  <Label
                    htmlFor={`apikey-scope-${item.value}`}
                    className="text-sm font-normal"
                  >
                    {item.label}
                  </Label>
                </div>
              ))}
              {scopes.length === 0 && (
                <p className="text-muted-foreground text-sm">
                  Choose at least one.
                </p>
              )}
            </fieldset>

            {createKey.isError && (
              <p className="text-destructive-text text-sm">
                The key was not created — {createKey.error.message}
              </p>
            )}

            <DialogFooter>
              <Button variant="ghost" onClick={() => close(false)}>
                Cancel
              </Button>
              <Button
                disabled={
                  !label.trim() || scopes.length === 0 || createKey.isPending
                }
                onClick={() =>
                  createKey.mutate(
                    { name: label.trim(), scopes },
                    { onSuccess: setIssued },
                  )
                }
              >
                <KeyRound className="mr-1.5 size-3.5" />
                {createKey.isPending ? "Creating…" : "Create key"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
