import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { MultiSelect } from "darkraise-ui/components/multi-select"
import { KeyRound } from "lucide-react"
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
 *  `ratify` is deliberately not here. It is not a scope at all — confirming a
 *  fact stays a human action.
 */
const SCOPE_ITEMS = [
  { value: "capture", label: "Save new memories" },
  { value: "read", label: "Search and read memories" },
  // `admin` covers three unrelated powers and the label has to carry all of
  // them: the push webhook, which is the ordinary reason to mint one of
  // these keys, the file-scoped reindex, and on /mcp `document_delete_subtree`
  // -- which erases every document under a uri prefix with no undo. Naming
  // only the erase leaves a webhook operator hunting for a narrower scope
  // that does not exist; naming only the webhook understates what a leak
  // costs.
  { value: "admin", label: "Receive push updates, reindex repositories, delete document subtrees" },
]

/**
 * Creating a key, in a dialog rather than inline on the card.
 *
 * The secret is shown ONCE, on the create response, and no read surface can
 * hand it back. Inline on the card it appeared below a form the reader had
 * usually scrolled past by the time it rendered. Here it replaces the form in
 * a box that will not close until dismissed, which is the only moment the
 * credential exists.
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
    <Dialog open={open} onOpenChange={close}>
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
            <div className="border-inset bg-muted/20 flex flex-col gap-1 rounded-md border border-dashed p-2.5">
              <code className="font-mono text-sm break-all">{issued.token}</code>
            </div>
            <p className="text-muted-foreground text-sm">
              To connect an MCP client with this key:
            </p>
            <McpConnectSnippets apiKey={issued.token} />
            <Button className="w-fit" onClick={() => close(false)}>
              I have copied it
            </Button>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              <Label htmlFor="apikey-label" className="text-muted-foreground text-sm">
                What is this key for?
              </Label>
              <Input
                id="apikey-label"
                placeholder="e.g. my laptop's assistant"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-1">
              <Label className="text-muted-foreground text-sm">
                What may it do?
              </Label>
              <MultiSelect
                items={SCOPE_ITEMS}
                value={scopes}
                onValueChange={(details) => setScopes(details.value)}
                placeholder="Choose at least one"
              />
            </div>

            <Button
              className="w-fit"
              disabled={!label.trim() || scopes.length === 0 || createKey.isPending}
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

            {createKey.isError && (
              <p className="text-destructive text-sm">
                The key was not created — {createKey.error.message}
              </p>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
