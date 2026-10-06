import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Badge } from "darkraise-ui/components/badge"
import {
  ArrowUp,
  Check,
  Folder,
  FolderGit2,
  ChevronRight,
  Loader2,
  Search,
} from "lucide-react"
import {
  fsList,
  useFsRoots,
  type FsListResponse,
} from "@/hooks/api/use-setup-api"

type Props = {
  apiBase: "/setup" | "/system"
  value: string
  onChange: (path: string) => void
  onConfirm: (path: string, result: FsListResponse) => void | Promise<void>
  disabled?: boolean
}

// The browser's own listing of `value`. Exported so a caller can tell
// whether the browser already shows an error before printing its own copy
// of it; react-query shares the one request between them.
export function useFolderListing(apiBase: Props["apiBase"], value: string) {
  return useQuery({
    queryKey: ["fs", apiBase, "list", value],
    queryFn: () => fsList(apiBase, value, false),
    enabled: Boolean(value),
    retry: false,
  })
}

export function ServerPathBrowser(props: Props) {
  return <FolderBrowser key={`${props.apiBase}:${props.value}`} {...props} />
}

function FolderBrowser({
  apiBase,
  value,
  onChange,
  onConfirm,
  disabled,
}: Props) {
  const roots = useFsRoots(apiBase)
  const [confirmationError, setError] = useState<string | null>(null)
  const [manual, setManual] = useState(value)
  const [filter, setFilter] = useState("")
  const [isConfirming, setIsConfirming] = useState(false)
  const query = useFolderListing(apiBase, value)
  const listing = query.data
  const isLoading = query.isFetching
  const error =
    confirmationError ?? query.error?.message ?? listing?.blocked_reason
  const reload = () => {
    setError(null)
    void query.refetch()
  }
  const busy = disabled || isConfirming
  const current = Boolean(value) && listing !== undefined
  const entries = current
    ? listing.entries.filter(
        (entry) =>
          entry.is_dir &&
          entry.name.toLowerCase().includes(filter.toLowerCase()),
      )
    : []
  const path = current ? listing.path : value
  const segments = path.split("/").filter(Boolean)

  const confirm = async () => {
    setIsConfirming(true)
    setError(null)
    try {
      const result = await fsList(apiBase, path, true)
      if (result.blocked_reason) throw new Error(result.blocked_reason)
      if (result.is_git)
        throw new Error(
          "Choose the parent folder that contains your repositories.",
        )
      await onConfirm(result.path, result)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <div className="bg-card overflow-hidden rounded-xl border">
      <div className="space-y-4 border-b p-4">
        <div>
          <h2 className="font-medium">Repository folder</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Choose the folder containing your code repositories. These folders
            are on the Darkmem server, not your computer.
          </p>
        </div>
        <div
          className="flex flex-wrap items-center gap-2"
          aria-label="Folder shortcuts"
        >
          {roots.isLoading && (
            <span className="text-muted-foreground text-sm">
              Loading locations…
            </span>
          )}
          {(roots.data?.roots ?? []).map((root) => (
            <Button
              key={root.path}
              variant={value === root.path ? "secondary" : "outline"}
              size="sm"
              disabled={busy}
              onClick={() => onChange(root.path)}
              title={root.path}
            >
              <Folder aria-hidden className="size-4" />
              {root.label}
            </Button>
          ))}
          {roots.isError && (
            <span role="alert" className="text-destructive text-sm">
              Locations unavailable. Enter a path below.
            </span>
          )}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (manual.trim()) {
              onChange(manual.trim())
              reload()
            }
          }}
        >
          <Input
            aria-label="Server folder path"
            value={manual}
            onChange={(e) => setManual(e.target.value)}
            placeholder="/app/data/repositories"
            className="min-w-0 font-mono text-sm"
            disabled={busy}
          />
          <Button
            type="submit"
            variant="outline"
            disabled={busy || !manual.trim()}
          >
            Open
          </Button>
        </form>
      </div>

      <div className="flex min-w-0 items-center gap-2 border-b px-3 py-2">
        <Button
          size="icon"
          variant="ghost"
          aria-label="Go to parent folder"
          disabled={busy || !current || !listing.parent}
          onClick={() => listing?.parent && onChange(listing.parent)}
        >
          <ArrowUp aria-hidden className="size-4" />
        </Button>
        <nav
          aria-label="Folder breadcrumbs"
          className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-sm"
        >
          {value ? (
            <>
              <button
                type="button"
                className="hover:bg-accent shrink-0 rounded px-2 py-1 focus-visible:outline-2"
                disabled={busy}
                onClick={() => onChange("/")}
              >
                /
              </button>
              {segments.map((segment, index) => (
                <span key={index} className="flex shrink-0 items-center gap-1">
                  <ChevronRight
                    aria-hidden
                    className="text-muted-foreground size-3"
                  />
                  <button
                    type="button"
                    className="hover:bg-accent rounded px-2 py-1 focus-visible:outline-2"
                    disabled={busy}
                    aria-current={
                      index === segments.length - 1 ? "location" : undefined
                    }
                    onClick={() =>
                      onChange("/" + segments.slice(0, index + 1).join("/"))
                    }
                  >
                    {segment}
                  </button>
                </span>
              ))}
            </>
          ) : (
            <span className="text-muted-foreground">
              Choose a location to begin
            </span>
          )}
        </nav>
      </div>
      {current && !error && (
        <div className="relative m-3">
          <Search
            aria-hidden
            className="text-muted-foreground absolute top-3 left-3 size-4"
          />
          <Input
            aria-label="Filter folders"
            placeholder="Filter folders…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-9"
            disabled={busy}
          />
        </div>
      )}
      <div
        className="h-44 overflow-y-auto px-3 pb-3"
        aria-busy={isLoading}
        aria-label="Folders"
      >
        {isLoading ? (
          <div
            role="status"
            className="text-muted-foreground flex h-full items-center justify-center gap-2 text-sm"
          >
            <Loader2 aria-hidden className="size-4 animate-spin" />
            Loading folders…
          </div>
        ) : error ? (
          <div className="space-y-3 p-5 text-center">
            <p role="alert" className="text-destructive text-sm break-words">
              {error}
            </p>
            <Button
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={reload}
            >
              Try again
            </Button>
          </div>
        ) : entries.length ? (
          entries.map((entry) => (
            <button
              key={entry.path}
              type="button"
              className="hover:bg-accent focus-visible:ring-ring flex w-full min-w-0 items-center gap-3 rounded-md px-3 py-3 text-left focus-visible:ring-2 focus-visible:outline-none disabled:opacity-50"
              disabled={busy}
              onClick={() => onChange(entry.path)}
            >
              {entry.is_git ? (
                <FolderGit2
                  aria-hidden
                  className="text-primary-text size-5 shrink-0"
                />
              ) : (
                <Folder
                  aria-hidden
                  className="text-muted-foreground size-5 shrink-0"
                />
              )}
              <span
                className="min-w-0 flex-1 truncate text-sm"
                title={entry.name}
              >
                {entry.name}
              </span>
              {entry.is_git && (
                <Badge variant="secondary">Git repository</Badge>
              )}
              {entry.has_repos && (
                <Badge variant="outline">{entry.repo_count} repos</Badge>
              )}
              <ChevronRight
                aria-hidden
                className="text-muted-foreground size-4 shrink-0"
              />
            </button>
          ))
        ) : (
          <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-2 text-center text-sm">
            <Folder aria-hidden className="size-8 opacity-50" />
            <p>
              {!value
                ? "Select a location above or enter a folder path."
                : filter
                  ? "No folders match your search."
                  : "No subfolders here. You can still use this folder."}
            </p>
          </div>
        )}
      </div>
      <div className="bg-muted/20 flex flex-col gap-3 border-t p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 text-sm">
          <p className="text-muted-foreground">
            {current && listing.is_git
              ? "This is a Git repository. Choose its parent folder."
              : "Repositories directly inside this folder will be detected."}
          </p>
          {value && <p className="mt-1 font-mono text-xs break-all">{path}</p>}
        </div>
        <Button
          className="shrink-0"
          onClick={confirm}
          disabled={busy || isLoading || !current || !!error || listing.is_git}
        >
          {isConfirming ? (
            <Loader2 aria-hidden className="size-4 animate-spin" />
          ) : (
            <Check aria-hidden className="size-4" />
          )}
          {isConfirming ? "Checking folder…" : "Use this folder"}
        </Button>
      </div>
    </div>
  )
}
