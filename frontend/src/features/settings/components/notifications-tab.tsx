import { useState } from "react"
import { Send } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { EmptyState, HelpTip } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"
import {
  useNotifications,
  useTestNotification,
  useUpdateNotifications,
} from "@/hooks/api"

const MASK = "***"

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {label}
      </span>
      {children}
    </div>
  )
}

/**
 * Outbound notifications. Narrow by design: one channel, one event.
 *
 * The bot token is served masked and never travels back, so the field shows
 * `***` when one is stored and saving it unchanged leaves the stored token
 * alone — otherwise editing the chat id would silently destroy the credential.
 */
export function NotificationsTab() {
  const query = useNotifications({ enabled: !DEMO })
  const update = useUpdateNotifications()
  const test = useTestNotification()

  const stored = query.data
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [chatId, setChatId] = useState<string | null>(null)
  const [onFailure, setOnFailure] = useState<boolean | null>(null)

  if (DEMO) {
    return (
      <EmptyState
        kind="empty"
        icon={Send}
        title="Notifications need a live instance"
        description="This tab reads and writes real credentials, so it is not backed by the demo fixture."
      />
    )
  }
  if (query.isError) {
    return (
      <EmptyState
        kind="failed"
        title="Couldn’t load notification settings"
        description="The /config/notifications request failed — this is an error, not an empty configuration."
      />
    )
  }
  if (query.isLoading || !stored) {
    return (
      <div className="max-w-2xl space-y-2">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-10 w-full rounded-md" />
        ))}
      </div>
    )
  }

  const on = enabled ?? stored.telegram.enabled
  const tok = token ?? stored.telegram.bot_token
  const chat = chatId ?? stored.telegram.chat_id
  const failure = onFailure ?? stored.notify_on.job_failure
  const dirty =
    on !== stored.telegram.enabled ||
    tok !== stored.telegram.bot_token ||
    chat !== stored.telegram.chat_id ||
    failure !== stored.notify_on.job_failure

  const save = () => {
    update
      .mutateAsync({
        telegram: { enabled: on, bot_token: tok, chat_id: chat },
        notify_on: { job_failure: failure },
      })
      .then(() => {
        setEnabled(null); setToken(null); setChatId(null); setOnFailure(null)
        toast.success("Notification settings saved")
      })
      .catch((err: unknown) =>
        toast.error("Couldn’t save notification settings", {
          description: err instanceof Error ? err.message : undefined,
        }),
      )
  }

  return (
    <div className="max-w-2xl space-y-4">
      <div className="text-muted-foreground flex items-center gap-1.5 text-sm">
        <span>
          Where darkmem tells you something went wrong while nobody was
          watching.
        </span>
        <HelpTip label="About notifications">
          A notifier, not an alerting system: no routing rules, no severities,
          no retry queue. A send that fails is logged and dropped, because a
          notifier that can take down the run it reports on is worse than none.
        </HelpTip>
      </div>

      <div className="border-inset bg-card flex flex-col gap-3 rounded-lg border p-3.5">
        <div className="flex items-center gap-2">
          <Send aria-hidden className="text-muted-foreground size-[var(--icon-size)]" />
          <span className="font-medium">Telegram</span>
          <Switch
            checked={on}
            onCheckedChange={setEnabled}
            aria-label="Telegram notifications enabled"
            className="ml-auto"
          />
        </div>

        <Field label="bot token">
          <Input
            value={tok}
            aria-label="Telegram bot token"
            type="password"
            placeholder="123456:ABC-DEF…"
            className="font-mono"
            onChange={(e) => setToken(e.target.value)}
          />
        </Field>
        {stored.telegram.bot_token === MASK && token === null && (
          <p className="text-muted-foreground text-sm">
            A token is stored. It is never sent back to this screen — leave the
            field as-is to keep it.
          </p>
        )}

        <Field label="chat id">
          <Input
            value={chat}
            aria-label="Telegram chat id"
            placeholder="-1001234567890"
            className="font-mono"
            onChange={(e) => setChatId(e.target.value)}
          />
        </Field>
      </div>

      <div className="border-inset bg-card flex items-center gap-2 rounded-lg border p-3.5">
        <div className="min-w-0 flex-1">
          <p className="font-medium">Notify on job failure</p>
          <p className="text-muted-foreground text-sm">
            One message per failed background run, with the job key and its
            error. A successful run is not news.
          </p>
        </div>
        <Switch
          checked={failure}
          onCheckedChange={setOnFailure}
          aria-label="Notify on job failure"
        />
      </div>

      <div className="flex items-center gap-2">
        <Button disabled={!dirty || update.isPending} onClick={save}>
          Save
        </Button>
        <Button
          variant="outline"
          disabled={test.isPending}
          onClick={() => {
            test
              .mutateAsync()
              .then((r) =>
                r.sent
                  ? toast.success("Test message sent")
                  : toast.error("Test message not sent", {
                      description: r.error ?? undefined,
                    }),
              )
              .catch((err: unknown) =>
                toast.error("Test failed", {
                  description: err instanceof Error ? err.message : undefined,
                }),
              )
          }}
        >
          Send test message
        </Button>
        {dirty && (
          <span className="text-muted-foreground text-sm">
            Unsaved changes — the test uses what is stored, not what is typed.
          </span>
        )}
      </div>
    </div>
  )
}
