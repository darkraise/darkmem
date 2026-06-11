import { useState } from "react"
import {
  UNIFIED_PALETTE,
  entityTypeColor,
  resolveNodeColor,
} from "@/features/graph/lib/graph-colors"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import { Input } from "darkraise-ui/components/input"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
import { ScrollArea } from "darkraise-ui/components/scroll-area"

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
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())

  function toggleGroup(group: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      next.has(group) ? next.delete(group) : next.add(group)
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
    <div className="flex min-h-0 flex-1 flex-col w-[280px] max-w-[calc(100vw-1.5rem)]">
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

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-4 p-3">
          {tagGroups.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1.5 text-sm font-semibold tracking-wider uppercase">
                Tags
              </p>
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
                                )
                              : "#8b949e",
                        }}
                      />
                      <span className="font-medium capitalize">{category}</span>
                      <span className="ml-auto opacity-60">
                        {collapsedGroups.has(category) ? "▶" : "▼"}
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
                        )
                      : "#8b949e"
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
                      ? UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length]
                      : "#8b949e"
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
                    const color = entityTypeColor(etype)
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
      </ScrollArea>

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
