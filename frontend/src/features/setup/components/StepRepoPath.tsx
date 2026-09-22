import { useEffect, useState } from "react"
import {
  useSetupWizardStore,
  type DetectedRepo,
} from "@/features/setup/setupWizardStore"
import { fsList, type FsListResponse } from "@/hooks/api/use-setup-api"
import { ServerPathBrowser } from "./ServerPathBrowser"

export function StepRepoPath() {
  const repos = useSetupWizardStore((s) => s.repos)
  const setReposBasePath = useSetupWizardStore((s) => s.setReposBasePath)
  const setReposDetected = useSetupWizardStore((s) => s.setReposDetected)

  const [browsePath, setBrowsePath] = useState(
    repos.basePath || "/app/data/repositories",
  )
  const [selectDefault, setSelectDefault] = useState(!repos.basePath)
  const [defaultError, setDefaultError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectDefault) return
    let cancelled = false
    fsList("/setup", browsePath, true)
      .then((result) => {
        if (cancelled) return
        if (result.blocked_reason) throw new Error(result.blocked_reason)
        if (result.is_git)
          throw new Error("Choose a folder containing repositories.")
        setReposBasePath(result.path)
        setReposDetected(detectedRepos(result))
      })
      .catch((error: Error) => {
        if (!cancelled) setDefaultError(error.message)
      })
    return () => {
      cancelled = true
    }
  }, [selectDefault, browsePath, setReposBasePath, setReposDetected])

  const browse = (path: string) => {
    setSelectDefault(false)
    setDefaultError(null)
    setBrowsePath(path)
    useSetupWizardStore.getState().setReposSkipped(false)
    setReposBasePath("")
    setReposDetected([])
  }

  const handleConfirm = (_path: string, result: FsListResponse) => {
    if (result.blocked_reason) throw new Error(result.blocked_reason)
    if (result.is_git)
      throw new Error("Choose a folder containing repositories.")
    setReposBasePath(result.path)
    setSelectDefault(false)
    setDefaultError(null)
    setReposDetected(detectedRepos(result))
  }

  return (
    <div className="space-y-4">
      <ServerPathBrowser
        apiBase="/setup"
        value={browsePath}
        onChange={browse}
        onConfirm={handleConfirm}
      />
      {defaultError && (
        <p role="alert" className="text-destructive text-sm">
          Could not select the default folder: {defaultError}. Choose another
          folder or retry with “Use this folder”.
        </p>
      )}
      {repos.basePath && (
        <div className="border-primary/30 bg-primary/5 rounded-lg border p-3 text-sm">
          Selected base path:{" "}
          <span className="font-mono break-all">{repos.basePath}</span>
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

function detectedRepos(result: FsListResponse): DetectedRepo[] {
  return result.entries
    .filter((entry) => entry.is_git)
    .map((entry) => ({
      name: entry.name,
      subPath: entry.name,
      selected: true,
    }))
}
