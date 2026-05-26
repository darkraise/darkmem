import { useEffect, useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Badge } from "darkraise-ui/components/badge"
import { Folder, FolderGit2, ChevronRight } from "lucide-react"
import { fsList, useFsRoots, type FsListEntry } from "@/hooks/api/use-setup-api"

type Props = {
  apiBase: "/setup" | "/system"
  value: string
  onChange: (path: string) => void
  onConfirm: (path: string) => void | Promise<void>
  disabled?: boolean
}

export function ServerPathBrowser({
  apiBase,
  value,
  onChange,
  onConfirm,
  disabled,
}: Props) {
  const { data: rootsData } = useFsRoots(apiBase)
  const [entries, setEntries] = useState<FsListEntry[]>([])
  const [parent, setParent] = useState<string | null>(null)
  const [isGit, setIsGit] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [manual, setManual] = useState(value)

  useEffect(() => {
    setManual(value)
  }, [value])

  useEffect(() => {
    if (!value) return
    let cancelled = false
    fsList(apiBase, value, false)
      .then((res) => {
        if (cancelled) return
        setEntries(res.entries)
        setParent(res.parent)
        setIsGit(res.is_git)
        setError(null)
      })
      .catch((e) => {
        if (cancelled) return
        setError((e as Error).message)
        setEntries([])
        setParent(null)
        setIsGit(false)
      })
    return () => {
      cancelled = true
    }
  }, [apiBase, value])

  const navigate = (path: string) => onChange(path)

  const handleManualGo = () => {
    if (manual.trim()) onChange(manual.trim())
  }

  const handleConfirm = async () => {
    setError(null)
    try {
      await fsList(apiBase, value, true)
      await onConfirm(value)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Server folder browser</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {(rootsData?.roots ?? []).map((r) => (
            <Button
              key={r.path}
              size="sm"
              variant={value === r.path ? "default" : "outline"}
              disabled={disabled}
              onClick={() => navigate(r.path)}
            >
              {r.label}
            </Button>
          ))}
        </div>

        <div className="flex gap-2">
          <Input
            value={manual}
            onChange={(e) => setManual(e.target.value)}
            placeholder="/absolute/path/to/folder"
            disabled={disabled}
          />
          <Button
            variant="outline"
            onClick={handleManualGo}
            disabled={disabled}
          >
            Go
          </Button>
        </div>

        {parent && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigate(parent)}
            disabled={disabled}
          >
            ..
          </Button>
        )}

        <div className="max-h-72 divide-y overflow-y-auto rounded-md border">
          {entries.map((entry) => (
            <button
              key={entry.path}
              type="button"
              className="hover:bg-accent flex w-full items-center gap-2 px-3 py-2 text-left"
              onClick={() => navigate(entry.path)}
              disabled={disabled}
            >
              {entry.is_git ? (
                <FolderGit2 className="h-4 w-4" />
              ) : (
                <Folder className="h-4 w-4" />
              )}
              <span className="flex-1 truncate">{entry.name}</span>
              {entry.is_git && <Badge variant="secondary">git</Badge>}
              {entry.has_repos && <Badge>{`repos:${entry.repo_count}`}</Badge>}
              <ChevronRight className="text-muted-foreground h-4 w-4" />
            </button>
          ))}
          {entries.length === 0 && !error && (
            <div className="text-muted-foreground px-3 py-6 text-center text-sm">
              No subfolders.
            </div>
          )}
        </div>

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        <div className="flex justify-end">
          <Button
            onClick={handleConfirm}
            disabled={disabled || !value || isGit}
          >
            Use this folder
          </Button>
        </div>
        {isGit && (
          <p className="text-muted-foreground text-xs">
            This folder is itself a git repository — pick its parent to register
            the repos inside.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
