import { useState } from "react";
import { ChevronDown, ChevronUp, FileText, Diamond } from "lucide-react";

interface SourceBadgesProps {
  memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
  entities: { id?: string; name?: string; entity_type?: string }[];
}

export function SourceBadges({ memories, entities }: SourceBadgesProps) {
  const [expanded, setExpanded] = useState(false);

  if (memories.length === 0 && entities.length === 0) return null;

  const entityCount = entities.filter((e) => e.name).length;

  return (
    <div className="mt-2.5">
      <button
        className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        {memories.length > 0 && (
          <span className="inline-flex items-center gap-1 bg-muted/80 px-2 py-0.5 rounded-md">
            <FileText className="w-3 h-3" />
            {memories.length} {memories.length === 1 ? "memory" : "memories"}
          </span>
        )}
        {entityCount > 0 && (
          <span className="inline-flex items-center gap-1 bg-muted/80 px-2 py-0.5 rounded-md">
            <Diamond className="w-3 h-3" />
            {entityCount} {entityCount === 1 ? "entity" : "entities"}
          </span>
        )}
        {expanded ? (
          <ChevronUp className="w-3 h-3" />
        ) : (
          <ChevronDown className="w-3 h-3" />
        )}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5 text-xs animate-in slide-in-from-top-1 duration-150">
          {memories.map((m, i) => (
            <div
              key={m.id ?? i}
              className="bg-muted/30 rounded-lg p-2.5 border border-border/50"
            >
              <div className="text-foreground/90 line-clamp-2 leading-relaxed">
                {m.content?.slice(0, 150) ?? `Memory ${m.id?.slice(0, 8)}`}
              </div>
              <div className="flex gap-3 mt-1.5 text-muted-foreground/60">
                {m.source && (
                  <span className="inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/40" />
                    {m.source}
                  </span>
                )}
                {m.score != null && (
                  <span>{Math.round(m.score * 100)}% match</span>
                )}
                {m.tags && m.tags.length > 0 && (
                  <span className="truncate">{m.tags.slice(0, 2).join(", ")}</span>
                )}
              </div>
            </div>
          ))}
          {entities
            .filter((e) => e.name)
            .map((e, i) => (
              <div
                key={e.id ?? i}
                className="flex items-center gap-2.5 bg-muted/30 rounded-lg p-2.5 border border-border/50"
              >
                <span
                  className="w-3 h-3 shrink-0"
                  style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)", backgroundColor: "#fb923c" }}
                />
                <span className="text-foreground/90 font-medium">{e.name}</span>
                {e.entity_type && (
                  <span className="text-muted-foreground/60 capitalize text-[10px] bg-muted px-1.5 py-0.5 rounded">
                    {e.entity_type}
                  </span>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
