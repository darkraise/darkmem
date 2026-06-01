import { useEffect } from "react"
import {
  useSetupWizardStore,
  type DetectedRepo,
} from "@/features/setup/setupWizardStore"
import { fsList } from "@/hooks/api/use-setup-api"
import { ServerPathBrowser } from "./ServerPathBrowser"

export function StepRepoPath() {
  const repos = useSetupWizardStore((s) => s.repos)
  const setReposBasePath = useSetupWizardStore((s) => s.setReposBasePath)
  const setReposDetected = useSetupWizardStore((s) => s.setReposDetected)

  useEffect(() => {
    if (!repos.basePath) setReposDetected([])
  }, [repos.basePath, setReposDetected])

  const handleConfirm = async (path: string) => {
    setReposBasePath(path)
    const result = await fsList("/setup", path, true)
    const detected: DetectedRepo[] = result.entries
      .filter((e) => e.is_git)
      .map((e) => ({
        name: e.name,
        subPath: e.name,
        selected: true,
      }))
    setReposDetected(detected)
  }

  return (
    <div className="space-y-4">
      <ServerPathBrowser
        apiBase="/setup"
        value={repos.basePath}
        onChange={setReposBasePath}
        onConfirm={handleConfirm}
      />
      {repos.basePath && (
        <div className="text-muted-foreground text-base">
          Selected base path:{" "}
          <span className="font-mono">{repos.basePath}</span>
          {repos.detected.length > 0 ? (
            <>
              {" "}
              — found <strong>{repos.detected.length}</strong> repository(ies).
              Review them on the next step.
            </>
          ) : (
            <> — no immediate-child repositories detected.</>
          )}
        </div>
      )}
    </div>
  )
}

export function isStepRepoPathValid(repos: {
  basePath: string
  skipped: boolean
}): boolean {
  if (repos.skipped) return true
  return repos.basePath.length > 0
}
