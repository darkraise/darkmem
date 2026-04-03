import { useState } from "react";

interface SourceBadgesProps {
  memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
  entities: { id?: string; name?: string; entity_type?: string }[];
}

export function SourceBadges({ memories, entities }: SourceBadgesProps) {
  const [expanded, setExpanded] = useState(false);

  if (memories.length === 0 && entities.length === 0) return null;

  const entityCount = entities.filter((e) => e.name).length;

  return (
    <div className="mt-2">
      <div
        className="flex gap-2 flex-wrap cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        {memories.length > 0 && (
          <span className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground">
            📄 {memories.length} {memories.length === 1 ? "memory" : "memories"}
          </span>
        )}
        {entityCount > 0 && (
          <span className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground">
            🔷 {entityCount} {entityCount === 1 ? "entity" : "entities"}
          </span>
        )}
        <span className="text-xs text-muted-foreground/50">
          {expanded ? "▲" : "▼"}
        </span>
      </div>

      {expanded && (
        <div className="mt-2 space-y-1.5 text-xs">
          {memories.map((m, i) => (
            <div
              key={m.id ?? i}
              className="bg-muted/50 rounded-md p-2 border border-border"
            >
              <div className="text-foreground line-clamp-2">
                {m.content?.slice(0, 120) ?? `Memory ${m.id?.slice(0, 8)}`}
              </div>
              <div className="flex gap-2 mt-1 text-muted-foreground">
                {m.source && <span>{m.source}</span>}
                {m.score != null && <span>relevance: {m.score}</span>}
                {m.tags && m.tags.length > 0 && (
                  <span>{m.tags.slice(0, 3).join(", ")}</span>
                )}
              </div>
            </div>
          ))}
          {entities
            .filter((e) => e.name)
            .map((e, i) => (
              <div
                key={e.id ?? i}
                className="flex items-center gap-2 bg-muted/50 rounded-md p-2 border border-border"
              >
                <span
                  className="w-2.5 h-2.5 shrink-0"
                  style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)", backgroundColor: "#fb923c" }}
                />
                <span className="text-foreground">{e.name}</span>
                {e.entity_type && (
                  <span className="text-muted-foreground capitalize">{e.entity_type}</span>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
