import { useState } from "react"
import { resolveNodeColor, entityTypeColor, clusterColor } from "@/features/graph/lib/graph-colors"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { Input } from "darkraise-ui/components/input"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "darkraise-ui/components/popover"
import { ChevronDown, Tags } from "lucide-react"

export interface GraphFilterPanelProps {
  tagGroups: [string, [string, number][]][]
  allTypes: [string, number][]
  allSources: [string, number][]
  allClusters: [number, number][]
  clusterNames: Record<string, string>
  selectedTags: Set<string>
  selectedTypes: Set<string>
  selectedSources: Set<string>
  selectedClusters: Set<number>
  searchText: string
  colorMode: ColorMode
  onSearchChange: (v: string) => void
  onTagToggle: (tag: string) => void
  onTypeToggle: (type: string) => void
  onSourceToggle: (src: string) => void
  onClusterToggle: (cid: number) => void
  onShowAll: () => void
  entityLayerEnabled?: boolean
  allEntityTypes?: [string, number][]
  selectedEntityTypes?: Set<string>
  onEntityTypeToggle?: (type: string) => void
}

export function GraphFilterPanel({
  tagGroups,
  allTypes,
  allSources,
  allClusters,
  clusterNames,
  selectedTags,
  selectedTypes,
  selectedSources,
  selectedClusters,
  searchText,
  colorMode,
  onSearchChange,
  onTagToggle,
  onTypeToggle,
  onSourceToggle,
  onClusterToggle,
  onShowAll,
  entityLayerEnabled,
  allEntityTypes,
  selectedEntityTypes,
  onEntityTypeToggle,
}: GraphFilterPanelProps) {
  // Open by default. Collapsing them made the popover show a list of group
  // headers to click through, when opening the popover was already the click
  // that asked for the tags. Folding the whole thing away is the trigger row's
  // job, not this one's.
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())
  const { palette } = useMemoryGraphTheme()

  function toggleGroup(group: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(group)) next.delete(group)
      else next.add(group)
      return next
    })
  }

  const hasFilters =
    searchText.trim() !== "" ||
    selectedTags.size > 0 ||
    selectedTypes.size > 0 ||
    selectedSources.size > 0 ||
    selectedClusters.size > 0

  return (
    <div className="flex h-full max-h-full min-h-0 w-[280px] max-w-[calc(100vw-1.5rem)] flex-col">
      <div className="border-border shrink-0 border-b p-3 pb-2">
        <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
          Search
        </p>
        <Input
          placeholder="Filter by content…"
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full"
        />
      </div>

      {/* Native overflow rather than ScrollArea: this sits inside an
          absolutely-positioned max-height wrapper, where the viewport
          ScrollArea renders had no bounded height to scroll within. */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="space-y-4 p-3">
          {tagGroups.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
                Tags
              </p>
              {/* Collapsed by default and opened in a popover: the tag list is
                  the longest thing in this panel by far, and left inline it
                  pushed every other filter below the fold. */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="flex w-full items-center gap-2 text-left"
                  >
                    <Tags aria-hidden className="h-3.5 w-3.5 shrink-0" />
                    <span className="flex-1 truncate">
                      {selectedTags.size > 0 ? "Tags selected" : "Any tag"}
                    </span>
                    {selectedTags.size > 0 && (
                      <span className="bg-primary/20 text-primary rounded-full px-1.5 py-0.5 font-mono text-[10px] tabular-nums">
                        {selectedTags.size}
                      </span>
                    )}
                    <ChevronDown
                      aria-hidden
                      className="text-muted-foreground h-3.5 w-3.5 shrink-0"
                    />
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  side="right"
                  align="start"
                  className="bg-card border-border max-h-[min(60vh,26rem)] w-[260px] overflow-y-auto rounded-lg border p-2 shadow-xl"
                >
                  <div className="space-y-2">
                    {tagGroups.map(([category, tags]) => (
                      <div key={category}>
                        <Button
                          variant="ghost"
                          className="text-muted-foreground hover:text-foreground mb-1 flex w-full items-center gap-1.5 text-left"
                          onClick={() => toggleGroup(category)}
                        >
                          <span
                            className="h-2 w-2 flex-shrink-0 rounded-full"
                            style={{
                              backgroundColor:
                                colorMode === "tag"
                                  ? resolveNodeColor(
                                      {
                                        cluster: -1,
                                        memory_type: null,
                                        tags: [category + "/x"],
                                      },
                                      "tag",
                                      palette,
                                    )
                                  : palette.unclustered,
                            }}
                          />
                          <span className="font-medium capitalize">
                            {category}
                          </span>
                          <span className="ml-auto opacity-60">
                            {collapsedGroups.has(category) ? "\u25b6" : "\u25bc"}
                          </span>
                        </Button>
                        {!collapsedGroups.has(category) && (
                          <div className="space-y-0.5 pl-1">
                            {tags.map(([tag, count]) => (
                              <Label
                                key={tag}
                                className="group flex cursor-pointer items-center gap-2 py-0.5 font-normal"
                              >
                                <Checkbox
                                  checked={selectedTags.has(tag)}
                                  onCheckedChange={() => onTagToggle(tag)}
                                  className="h-3.5 w-3.5"
                                />
                                <span
                                  className={`flex-1 truncate ${
                                    selectedTags.has(tag)
                                      ? "text-foreground"
                                      : "text-muted-foreground group-hover:text-foreground"
                                  }`}
                                  title={tag}
                                >
                                  {tag.includes("/")
                                    ? tag.split("/").slice(1).join("/")
                                    : tag}
                                </span>
                                <span className="text-sm opacity-40">
                                  {count}
                                </span>
                              </Label>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          )}

          {allTypes.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
                Types
              </p>
              <div className="space-y-0.5">
                {allTypes.map(([type, count]) => {
                  const realType = type === "(none)" ? null : type
                  const color =
                    colorMode === "type"
                      ? resolveNodeColor(
                          { cluster: -1, memory_type: realType, tags: [] },
                          "type",
                          palette,
                        )
                      : palette.unclustered
                  return (
                    <Label
                      key={type}
                      className="group flex cursor-pointer items-center gap-2 py-0.5 font-normal"
                    >
                      <Checkbox
                        checked={selectedTypes.has(type)}
                        onCheckedChange={() => onTypeToggle(type)}
                        className="h-3.5 w-3.5"
                      />
                      <span
                        className="h-2 w-2 flex-shrink-0 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span
                        className={`flex-1 truncate ${
                          selectedTypes.has(type)
                            ? "text-foreground"
                            : "text-muted-foreground group-hover:text-foreground"
                        }`}
                      >
                        {type}
                      </span>
                      <span className="text-sm opacity-40">{count}</span>
                    </Label>
                  )
                })}
              </div>
            </div>
          )}

          {allSources.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
                Sources
              </p>
              <div className="space-y-0.5">
                {allSources.map(([src, count]) => (
                  <Label
                    key={src}
                    className="group flex cursor-pointer items-center gap-2 py-0.5 font-normal"
                  >
                    <Checkbox
                      checked={selectedSources.has(src)}
                      onCheckedChange={() => onSourceToggle(src)}
                      className="h-3.5 w-3.5"
                    />
                    <span
                      className={`flex-1 truncate ${
                        selectedSources.has(src)
                          ? "text-foreground"
                          : "text-muted-foreground group-hover:text-foreground"
                      }`}
                      title={src}
                    >
                      {src}
                    </span>
                    <span className="text-sm opacity-40">{count}</span>
                  </Label>
                ))}
              </div>
            </div>
          )}

          {allClusters.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
                Clusters
              </p>
              <div className="space-y-0.5">
                {allClusters.map(([cid, count]) => {
                  const color =
                    colorMode === "cluster"
                      ? clusterColor(palette, cid)
                      : palette.unclustered
                  return (
                    <Label
                      key={cid}
                      className="group flex cursor-pointer items-center gap-2 py-0.5 font-normal"
                    >
                      <Checkbox
                        checked={selectedClusters.has(cid)}
                        onCheckedChange={() => onClusterToggle(cid)}
                        className="h-3.5 w-3.5"
                      />
                      <span
                        className="h-2 w-2 flex-shrink-0 rounded-full opacity-70"
                        style={{ backgroundColor: color }}
                      />
                      <span
                        className={`flex-1 ${
                          selectedClusters.has(cid)
                            ? "text-foreground"
                            : "text-muted-foreground group-hover:text-foreground"
                        }`}
                      >
                        {clusterNames[String(cid)] || `Cluster ${cid}`}
                      </span>
                      <span className="text-sm opacity-40">{count}</span>
                    </Label>
                  )
                })}
              </div>
            </div>
          )}

          {entityLayerEnabled &&
            allEntityTypes &&
            allEntityTypes.length > 0 && (
              <div>
                <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
                  Entity Types
                </p>
                <div className="space-y-0.5">
                  {allEntityTypes.map(([etype, count]) => {
                    const color = entityTypeColor(etype, palette)
                    return (
                      <Label
                        key={etype}
                        className="group flex cursor-pointer items-center gap-2 py-0.5 font-normal"
                      >
                        <Checkbox
                          checked={selectedEntityTypes?.has(etype) ?? false}
                          onCheckedChange={() => onEntityTypeToggle?.(etype)}
                          className="h-3.5 w-3.5"
                        />
                        <span
                          className="h-2 w-2 flex-shrink-0"
                          style={{
                            backgroundColor: color,
                            clipPath:
                              "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
                          }}
                        />
                        <span
                          className={`flex-1 truncate capitalize ${
                            selectedEntityTypes?.has(etype)
                              ? "text-foreground"
                              : "text-muted-foreground group-hover:text-foreground"
                          }`}
                        >
                          {etype}
                        </span>
                        <span className="text-sm opacity-40">{count}</span>
                      </Label>
                    )
                  })}
                </div>
              </div>
            )}
        </div>
      </div>

      <div className="border-border shrink-0 border-t p-3">
        <Button
          variant="outline"
          className="w-full"
          onClick={onShowAll}
          disabled={!hasFilters}
        >
          Show All
        </Button>
      </div>
    </div>
  )
}
