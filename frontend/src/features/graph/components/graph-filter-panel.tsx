import { useState } from "react";
import { UNIFIED_PALETTE, UNCLUSTERED_COLOR, entityTypeColor, resolveNodeColor } from "@/features/graph/lib/graph-colors";
import type { ColorMode } from "@/features/graph/lib/graph-colors";
import { Input } from "darkraise-ui/components/input";
import { Checkbox } from "darkraise-ui/components/checkbox";
import { Label } from "darkraise-ui/components/label";
import { Button } from "darkraise-ui/components/button";

export interface GraphFilterPanelProps {
  tagGroups: [string, [string, number][]][];
  allTypes: [string, number][];
  allSources: [string, number][];
  allClusters: [number, number][];
  clusterNames: Record<string, string>;
  selectedTags: Set<string>;
  selectedTypes: Set<string>;
  selectedSources: Set<string>;
  selectedClusters: Set<number>;
  searchText: string;
  colorMode: ColorMode;
  onSearchChange: (v: string) => void;
  onTagToggle: (tag: string) => void;
  onTypeToggle: (type: string) => void;
  onSourceToggle: (src: string) => void;
  onClusterToggle: (cid: number) => void;
  onShowAll: () => void;
  entityLayerEnabled?: boolean;
  allEntityTypes?: [string, number][];
  selectedEntityTypes?: Set<string>;
  onEntityTypeToggle?: (type: string) => void;
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
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(),
  );

  function toggleGroup(group: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      next.has(group) ? next.delete(group) : next.add(group);
      return next;
    });
  }

  const hasFilters =
    searchText.trim() !== "" ||
    selectedTags.size > 0 ||
    selectedTypes.size > 0 ||
    selectedSources.size > 0 ||
    selectedClusters.size > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0" style={{ width: 280 }}>
      <div className="p-3 pb-2 border-b border-border shrink-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Search
        </p>
        <Input
          placeholder="Filter by content…"
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full text-sm"
        />
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
        <div className="p-3 space-y-4">
          {tagGroups.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Tags
              </p>
              <div className="space-y-2">
                {tagGroups.map(([category, tags]) => (
                  <div key={category}>
                    <button
                      className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground w-full text-left mb-1"
                      onClick={() => toggleGroup(category)}
                    >
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: colorMode === "tag" ? resolveNodeColor({ cluster: -1, memory_type: null, tags: [category + "/x"] }, "tag") : "#8b949e" }}
                      />
                      <span className="font-medium capitalize">{category}</span>
                      <span className="ml-auto opacity-60">
                        {collapsedGroups.has(category) ? "▶" : "▼"}
                      </span>
                    </button>
                    {!collapsedGroups.has(category) && (
                      <div className="space-y-0.5 pl-1">
                        {tags.map(([tag, count]) => (
                          <Label
                            key={tag}
                            className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group font-normal"
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
                            <span className="opacity-40 text-xs">{count}</span>
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
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Types
              </p>
              <div className="space-y-0.5">
                {allTypes.map(([type, count]) => {
                  const realType = type === "(none)" ? null : type;
                  const color = colorMode === "type"
                    ? resolveNodeColor({ cluster: -1, memory_type: realType, tags: [] }, "type")
                    : "#8b949e";
                  return (
                    <Label
                      key={type}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group font-normal"
                    >
                      <Checkbox
                        checked={selectedTypes.has(type)}
                        onCheckedChange={() => onTypeToggle(type)}
                        className="h-3.5 w-3.5"
                      />
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
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
                      <span className="opacity-40 text-xs">{count}</span>
                    </Label>
                  );
                })}
              </div>
            </div>
          )}

          {allSources.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Sources
              </p>
              <div className="space-y-0.5">
                {allSources.map(([src, count]) => (
                  <Label
                    key={src}
                    className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group font-normal"
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
                    <span className="opacity-40 text-xs">{count}</span>
                  </Label>
                ))}
              </div>
            </div>
          )}

          {allClusters.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Clusters
              </p>
              <div className="space-y-0.5">
                {allClusters.map(([cid, count]) => {
                  const color = colorMode === "cluster"
                    ? UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length]
                    : "#8b949e";
                  return (
                    <Label
                      key={cid}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group font-normal"
                    >
                      <Checkbox
                        checked={selectedClusters.has(cid)}
                        onCheckedChange={() => onClusterToggle(cid)}
                        className="h-3.5 w-3.5"
                      />
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0 opacity-70"
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
                      <span className="opacity-40 text-xs">{count}</span>
                    </Label>
                  );
                })}
              </div>
            </div>
          )}

          {entityLayerEnabled && allEntityTypes && allEntityTypes.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Entity Types
              </p>
              <div className="space-y-0.5">
                {allEntityTypes.map(([etype, count]) => {
                  const color = entityTypeColor(etype);
                  return (
                    <Label
                      key={etype}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group font-normal"
                    >
                      <Checkbox
                        checked={selectedEntityTypes?.has(etype) ?? false}
                        onCheckedChange={() => onEntityTypeToggle?.(etype)}
                        className="h-3.5 w-3.5"
                      />
                      <span
                        className="w-2 h-2 flex-shrink-0"
                        style={{ backgroundColor: color, clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)" }}
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
                      <span className="opacity-40 text-xs">{count}</span>
                    </Label>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="p-3 border-t border-border shrink-0">
        <Button
          variant="outline"
          className="w-full text-sm"
          onClick={onShowAll}
          disabled={!hasFilters}
        >
          Show All
        </Button>
      </div>
    </div>
  );
}
