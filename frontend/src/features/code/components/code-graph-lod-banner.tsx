import { useMemo } from "react"
import { CornerLeftUp, Layers, ScanSearch } from "lucide-react"
import { Banner } from "darkraise-ui/components/banner"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import type { CodeGraphData } from "@/hooks/api"

/** The folders one level below `scope` that hold drawn files, with how many
 *  files each holds — the choices for drilling one level deeper. */
export function childFolders(
  filePaths: readonly string[],
  scope: string | null,
): { path: string; name: string; files: number }[] {
  const prefix = scope ? `${scope}/` : ""
  const counts = new Map<string, number>()
  for (const path of filePaths) {
    if (!path.startsWith(prefix)) continue
    const slash = path.indexOf("/", prefix.length)
    if (slash === -1) continue
    const folder = path.slice(0, slash)
    counts.set(folder, (counts.get(folder) ?? 0) + 1)
  }
  return [...counts]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([path, files]) => ({
      path,
      name: path.slice(prefix.length),
      files,
    }))
}

function parentOf(scope: string): string | null {
  const slash = scope.lastIndexOf("/")
  return slash === -1 ? null : scope.slice(0, slash)
}

const n = (value: number | undefined) => (value ?? 0).toLocaleString()

/**
 * Says what the Code Graph is drawing when it is not the whole symbol graph:
 * folded to files (GET /code/graph's `level=file`, chosen by `auto` above its
 * node limit) or narrowed to one file or folder. A small repository's whole
 * symbol graph has no banner — nothing is folded or hidden.
 */
export function CodeGraphLodBanner({
  raw,
  selectedFile,
  onScope,
}: {
  raw: CodeGraphData
  /** A file node selected on the folded graph, offered as a drill target. */
  selectedFile: string | null
  onScope: (scope: string | null) => void
}) {
  const scope = raw.scope ?? null
  const folded = raw.level === "file"
  const folders = useMemo(
    () =>
      folded
        ? childFolders(
            raw.nodes.filter((n) => n.kind === "file").map((n) => n.id),
            scope,
          )
        : [],
    [folded, raw.nodes, scope],
  )

  if (!folded && scope === null) return null
  const stats = raw.stats
  const parent = scope === null ? null : parentOf(scope)

  return (
    <Banner
      variant={folded ? "info" : "default"}
      icon={
        folded ? (
          <Layers aria-hidden className="h-4 w-4" />
        ) : (
          <ScanSearch aria-hidden className="h-4 w-4" />
        )
      }
      className="rounded-none border-x-0 border-t-0"
      aria-label="Graph level of detail"
    >
      <div className="flex flex-col gap-2">
        {folded ? (
          <p className="text-sm">
            <b>Folded to files{scope ? ` in ${scope}` : ""}.</b>{" "}
            {n(stats?.symbols)} symbols and {n(stats?.symbol_edges)} symbol
            edges are drawn as {n(stats?.files_drawn)} files and{" "}
            {n(stats?.file_edges)} file → file edges; a thicker edge folds more
            calls.
            {(stats?.files_without_symbols ?? 0) > 0 &&
              ` ${n(stats?.files_without_symbols)} files that define no symbol are not drawn.`}
            {(stats?.boundary_edges ?? 0) > 0 &&
              ` ${n(stats?.boundary_edges)} symbol edges leave this folder.`}{" "}
            Open a file in the explorer or drill into a folder to see its
            symbols.
          </p>
        ) : (
          <p className="text-sm">
            Showing the symbols in <b className="font-mono">{scope}</b>.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {folders.length > 0 && (
            <Select value="" onValueChange={(value) => value && onScope(value)}>
              <SelectTrigger className="w-64" aria-label="Drill into a folder">
                <SelectValue placeholder="Drill into a folder…" />
              </SelectTrigger>
              <SelectContent>
                {folders.map((folder) => (
                  <SelectItem key={folder.path} value={folder.path}>
                    {folder.name}/ · {folder.files.toLocaleString()}{" "}
                    {folder.files === 1 ? "file" : "files"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {folded && selectedFile && (
            <Button variant="outline" onClick={() => onScope(selectedFile)}>
              Show symbols in {selectedFile.split("/").pop()}
            </Button>
          )}
          {scope !== null && (
            <>
              <Button variant="ghost" onClick={() => onScope(parent)}>
                <CornerLeftUp aria-hidden className="mr-1 h-3.5 w-3.5" />
                {parent ? `Up to ${parent}` : "Up to the whole repository"}
              </Button>
              {parent && (
                <Button variant="ghost" onClick={() => onScope(null)}>
                  Whole repository
                </Button>
              )}
            </>
          )}
        </div>
      </div>
    </Banner>
  )
}
