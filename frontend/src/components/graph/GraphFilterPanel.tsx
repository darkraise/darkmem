import { useState } from "react";
import { clusterColor, typeColor } from "@/lib/graph-colors";

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
  onSearchChange: (v: string) => void;
  onTagToggle: (tag: string) => void;
  onTypeToggle: (type: string) => void;
  onSourceToggle: (src: string) => void;
  onClusterToggle: (cid: number) => void;
  onShowAll: () => void;
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
  onSearchChange,
  onTagToggle,
  onTypeToggle,
  onSourceToggle,
  onClusterToggle,
  onShowAll,
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
      {/* Fixed search header */}
      <div className="p-3 pb-2 border-b border-border shrink-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Search
        </p>
        <input
          type="text"
          placeholder="Filter by content…"
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full text-sm bg-background border border-border rounded px-2 py-1.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary"
        />
      </div>

      {/* Scrollable filter sections */}
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
        <div className="p-3 space-y-4">
          {/* Tags */}
          {tagGroups.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Tags
              </p>
              <div className="space-y-2">
                {tagGroups.map(([category, tags]) => (
                  <div key={category}>
                    <button
                      className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground w-full text-left mb-1"
                      onClick={() => toggleGroup(category)}
                    >
                      <span className="font-medium capitalize">{category}</span>
                      <span className="ml-auto opacity-60">
                        {collapsedGroups.has(category) ? "▶" : "▼"}
                      </span>
                    </button>
                    {!collapsedGroups.has(category) && (
                      <div className="space-y-0.5 pl-1">
                        {tags.map(([tag, count]) => (
                          <label
                            key={tag}
                            className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                          >
                            <input
                              type="checkbox"
                              checked={selectedTags.has(tag)}
                              onChange={() => onTagToggle(tag)}
                              className="accent-primary w-3.5 h-3.5"
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
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Types */}
          {allTypes.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Types
              </p>
              <div className="space-y-0.5">
                {allTypes.map(([type, count]) => {
                  const realType = type === "(none)" ? null : type;
                  const color = typeColor(realType);
                  return (
                    <label
                      key={type}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                    >
                      <input
                        type="checkbox"
                        checked={selectedTypes.has(type)}
                        onChange={() => onTypeToggle(type)}
                        className="accent-primary w-3.5 h-3.5"
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
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Sources */}
          {allSources.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Sources
              </p>
              <div className="space-y-0.5">
                {allSources.map(([src, count]) => (
                  <label
                    key={src}
                    className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                  >
                    <input
                      type="checkbox"
                      checked={selectedSources.has(src)}
                      onChange={() => onSourceToggle(src)}
                      className="accent-primary w-3.5 h-3.5"
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
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Clusters */}
          {allClusters.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Clusters
              </p>
              <div className="space-y-0.5">
                {allClusters.map(([cid, count]) => {
                  const color = clusterColor(cid);
                  return (
                    <label
                      key={cid}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                    >
                      <input
                        type="checkbox"
                        checked={selectedClusters.has(cid)}
                        onChange={() => onClusterToggle(cid)}
                        className="accent-primary w-3.5 h-3.5"
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
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Show All button */}
      <div className="p-3 border-t border-border shrink-0">
        <button
          className={`w-full text-sm py-1.5 rounded border transition-colors ${
            hasFilters
              ? "border-primary text-primary hover:bg-primary/10"
              : "border-border text-muted-foreground cursor-default opacity-50"
          }`}
          onClick={onShowAll}
          disabled={!hasFilters}
        >
          Show All
        </button>
      </div>
    </div>
  );
}
