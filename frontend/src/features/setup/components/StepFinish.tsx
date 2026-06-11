import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Checkbox } from "darkraise-ui/components/checkbox"
import {
  useSetupWizardStore,
  PURPOSES,
} from "@/features/setup/setupWizardStore"

export function StepFinish() {
  const password = useSetupWizardStore((s) => s.password)
  const llm = useSetupWizardStore((s) => s.llm)
  const repos = useSetupWizardStore((s) => s.repos)
  const toggle = useSetupWizardStore((s) => s.toggleRepoSelected)
  const rename = useSetupWizardStore((s) => s.renameDetectedRepo)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Admin password</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {password.value ? "Set" : "Not set"}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Default LLM provider</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {llm.skipped || !llm.api_kind ? (
            <span className="text-muted-foreground">
              Skipped — system defaults will be used.
            </span>
          ) : (
            <>
              <div>
                <strong className="capitalize">{llm.api_kind}</strong>{" "}
                <span className="text-muted-foreground">
                  (default vendor menu seeded; api key applied to this row)
                </span>
              </div>
              <ul className="ml-4 list-disc">
                {PURPOSES.filter(
                  (p) =>
                    (p !== "embedding" || llm.supports_embedding) &&
                    llm.perPurpose[p].model,
                ).map((p) => (
                  <li key={p}>
                    <span className="capitalize">{p}</span>:{" "}
                    <span className="font-mono">{llm.perPurpose[p].model}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Default code repo path</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {repos.skipped || !repos.basePath ? (
            <span className="text-muted-foreground">
              Skipped — configure later under Settings.
            </span>
          ) : (
            <>
              <div>
                Base path: <span className="font-mono">{repos.basePath}</span>
              </div>
              {repos.detected.length === 0 ? (
                <div className="text-muted-foreground">
                  No repositories detected.
                </div>
              ) : (
                <div className="space-y-1">
                  {repos.detected.map((r) => (
                    <div
                      key={r.subPath}
                      className="flex min-w-0 items-center gap-2"
                    >
                      <Checkbox
                        checked={r.selected}
                        onCheckedChange={() => toggle(r.subPath)}
                        aria-label={`Import ${r.name}`}
                      />
                      <Input
                        className="h-8 flex-1"
                        value={r.name}
                        onChange={(e) => rename(r.subPath, e.target.value)}
                        aria-label={`Rename ${r.subPath}`}
                      />
                      <span className="text-muted-foreground truncate font-mono text-sm">
                        {r.subPath}
                      </span>
                    </div>
                  ))}
                  <div className="text-muted-foreground pt-2 text-sm">
                    Imported repositories start with auto-sync{" "}
                    <strong>off</strong>. Open the Repositories page and enable
                    each one from its Edit dialog when you're ready to have
                    darkmem fetch and re-index it on a schedule.
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
