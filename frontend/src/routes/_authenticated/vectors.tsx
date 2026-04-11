import { createFileRoute } from "@tanstack/react-router";
import { useVectorProjection } from "@/hooks/api";
import { useRef, useEffect, useState, useCallback, useMemo } from "react";

export const Route = createFileRoute("/_authenticated/vectors")({
  component: VectorSpacePage,
});

const PALETTE = [
  "#58a6ff",
  "#3fb950",
  "#d2a8ff",
  "#ffa657",
  "#f778ba",
  "#a371f7",
  "#f85149",
  "#56d364",
];
const FALLBACK_COLOR = "#8b949e";

interface VPoint {
  memory_id: string;
  x: number;
  y: number;
  content: string;
  source: string;
  tags: string[];
  memory_type: string | null;
}

const PAD = 56;
const TICK_VALUES = [-1.0, -0.5, 0.0, 0.5, 1.0];

function VectorSpacePage() {
  const { data, isLoading } = useVectorProjection();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hovered, setHovered] = useState<(VPoint & { screenX: number; screenY: number }) | null>(null);

  const points: VPoint[] = data?.points || [];

  const sourceColors = useMemo(() => {
    const uniqueSources = Array.from(
      new Set(points.map((p) => p.source ?? "unknown"))
    ).sort();
    const map = new Map<string, string>();
    uniqueSources.forEach((source, index) => {
      map.set(source, PALETTE[index % PALETTE.length]);
    });
    return map;
  }, [points]);

  const getColor = useCallback(
    (source: string): string => sourceColors.get(source) ?? FALLBACK_COLOR,
    [sourceColors]
  );

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || points.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    const w = rect.width;
    const h = rect.height;

    ctx.fillStyle = "#161b22";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "#21262d";
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
      const gx = PAD + (i / 4) * (w - 2 * PAD);
      const gy = PAD + (i / 4) * (h - 2 * PAD);
      ctx.beginPath(); ctx.moveTo(gx, PAD); ctx.lineTo(gx, h - PAD); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(PAD, gy); ctx.lineTo(w - PAD, gy); ctx.stroke();
    }

    ctx.fillStyle = "#484f58";
    ctx.font = "10px Inter, sans-serif";
    for (let i = 0; i <= 4; i++) {
      const gx = PAD + (i / 4) * (w - 2 * PAD);
      const gy = PAD + (i / 4) * (h - 2 * PAD);
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(TICK_VALUES[i].toFixed(1), gx, h - PAD + 4);
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(TICK_VALUES[4 - i].toFixed(1), PAD - 6, gy);
    }

    ctx.fillStyle = "#484f58";
    ctx.font = "12px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText("PCA Component 1", w / 2, h - PAD + 18);

    ctx.save();
    ctx.translate(PAD - 36, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textBaseline = "middle";
    ctx.fillText("PCA Component 2", 0, 0);
    ctx.restore();

    for (const p of points) {
      const px = PAD + ((p.x + 1) / 2) * (w - 2 * PAD);
      const py = PAD + ((1 - (p.y + 1) / 2)) * (h - 2 * PAD);
      ctx.beginPath();
      ctx.arc(px, py, 5, 0, Math.PI * 2);
      ctx.fillStyle = getColor(p.source);
      ctx.fill();
      ctx.strokeStyle = "#30363d";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }, [points, getColor]);

  useEffect(() => {
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [draw]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || points.length === 0) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const w = rect.width;
    const h = rect.height;

    let closest: (VPoint & { screenX: number; screenY: number }) | null = null;
    let minDist = 15;

    for (const p of points) {
      const px = PAD + ((p.x + 1) / 2) * (w - 2 * PAD);
      const py = PAD + ((1 - (p.y + 1) / 2)) * (h - 2 * PAD);
      const dist = Math.sqrt((mx - px) ** 2 + (my - py) ** 2);
      if (dist < minDist) {
        minDist = dist;
        closest = { ...p, screenX: e.clientX, screenY: e.clientY };
      }
    }
    setHovered(closest);
  }, [points]);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Vector Space</h2>
        {points.length > 0 && (
          <span className="text-sm text-muted-foreground">{points.length} memories projected (PCA 2D)</span>
        )}
      </div>
      {isLoading && <p className="text-muted-foreground">Loading vectors...</p>}
      {!isLoading && points.length === 0 && (
        <p className="text-muted-foreground">
          No vectors yet. Create memories with the pipeline running to generate embeddings.
        </p>
      )}
      {points.length > 0 && (
        <div className="relative bg-card border border-border rounded-lg overflow-hidden" style={{ height: "70vh" }}>
          <canvas
            ref={canvasRef}
            className="w-full h-full cursor-crosshair"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHovered(null)}
          />
          {hovered && (
            <div
              className="absolute pointer-events-none bg-card border border-border rounded-lg p-3 shadow-lg max-w-xs z-10"
              style={{
                left: Math.min(
                  hovered.screenX - (canvasRef.current?.getBoundingClientRect().left || 0) + 12,
                  (canvasRef.current?.getBoundingClientRect().width || 300) - 260
                ),
                top: hovered.screenY - (canvasRef.current?.getBoundingClientRect().top || 0) - 10,
              }}
            >
              <p className="text-xs text-foreground">{hovered.content}</p>
              <div className="flex gap-1 mt-2 flex-wrap">
                {hovered.tags?.map((t) => (
                  <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary">{t}</span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {hovered.source} {hovered.memory_type && `| ${hovered.memory_type}`}
              </p>
            </div>
          )}
        </div>
      )}
      {points.length > 0 && sourceColors.size > 0 && (
        <div className="mt-4 flex gap-3 flex-wrap">
          {Array.from(sourceColors.entries()).map(([source, color]) => (
            <div key={source} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
              {source}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
