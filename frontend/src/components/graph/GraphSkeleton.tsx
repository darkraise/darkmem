interface SkelCluster {
  color: string;
  hull: { cx: string; cy: string; rx: string; ry: string; rotate: string };
  nodes: { top: string; left: string; size: string; delay: string }[];
}

const SKEL_CLUSTERS: SkelCluster[] = [
  {
    // Purple cluster (left)
    color: "168,85,247",
    hull: { cx: "22%", cy: "38%", rx: "14%", ry: "18%", rotate: "-10deg" },
    nodes: [
      { top: "32%", left: "18%", size: "44px", delay: "0s" },
      { top: "24%", left: "26%", size: "34px", delay: "0.3s" },
      { top: "44%", left: "28%", size: "28px", delay: "0.6s" },
      { top: "28%", left: "12%", size: "26px", delay: "0.9s" },
      { top: "40%", left: "14%", size: "22px", delay: "0.4s" },
      { top: "48%", left: "22%", size: "20px", delay: "0.7s" },
      { top: "36%", left: "30%", size: "24px", delay: "0.2s" },
    ],
  },
  {
    // Green cluster (right)
    color: "63,185,80",
    hull: { cx: "65%", cy: "42%", rx: "15%", ry: "16%", rotate: "8deg" },
    nodes: [
      { top: "38%", left: "62%", size: "42px", delay: "0.2s" },
      { top: "30%", left: "72%", size: "32px", delay: "0.5s" },
      { top: "48%", left: "68%", size: "28px", delay: "0.8s" },
      { top: "46%", left: "56%", size: "30px", delay: "0.4s" },
      { top: "36%", left: "76%", size: "22px", delay: "0.1s" },
      { top: "52%", left: "60%", size: "20px", delay: "0.6s" },
      { top: "42%", left: "74%", size: "24px", delay: "0.3s" },
    ],
  },
  {
    // Blue cluster (top-center)
    color: "88,166,255",
    hull: { cx: "46%", cy: "20%", rx: "13%", ry: "12%", rotate: "5deg" },
    nodes: [
      { top: "16%", left: "44%", size: "36px", delay: "0.1s" },
      { top: "12%", left: "36%", size: "26px", delay: "0.7s" },
      { top: "22%", left: "52%", size: "28px", delay: "0.4s" },
      { top: "18%", left: "56%", size: "22px", delay: "0.8s" },
      { top: "10%", left: "46%", size: "20px", delay: "0.5s" },
      { top: "24%", left: "40%", size: "24px", delay: "0.2s" },
    ],
  },
  {
    // Orange cluster (bottom)
    color: "255,166,87",
    hull: { cx: "42%", cy: "68%", rx: "14%", ry: "13%", rotate: "-5deg" },
    nodes: [
      { top: "64%", left: "38%", size: "38px", delay: "0.3s" },
      { top: "70%", left: "48%", size: "30px", delay: "0.6s" },
      { top: "58%", left: "46%", size: "26px", delay: "0.1s" },
      { top: "72%", left: "36%", size: "22px", delay: "0.5s" },
      { top: "66%", left: "52%", size: "24px", delay: "0.8s" },
      { top: "60%", left: "32%", size: "20px", delay: "0.4s" },
    ],
  },
  {
    // Cyan cluster (far right, smaller)
    color: "6,182,212",
    hull: { cx: "84%", cy: "24%", rx: "10%", ry: "11%", rotate: "12deg" },
    nodes: [
      { top: "20%", left: "82%", size: "32px", delay: "0.2s" },
      { top: "14%", left: "88%", size: "24px", delay: "0.6s" },
      { top: "28%", left: "86%", size: "22px", delay: "0.9s" },
      { top: "22%", left: "78%", size: "20px", delay: "0.4s" },
    ],
  },
];

const SKEL_EDGES: { top: string; left: string; width: string; rotate: string; delay: string }[] = [
  // Intra-cluster edges (purple)
  { top: "34%", left: "20%", width: "70px", rotate: "-12deg", delay: "0.2s" },
  { top: "30%", left: "16%", width: "55px", rotate: "35deg", delay: "0.5s" },
  { top: "42%", left: "18%", width: "60px", rotate: "15deg", delay: "0.8s" },
  // Intra-cluster edges (green)
  { top: "40%", left: "60%", width: "80px", rotate: "18deg", delay: "0.3s" },
  { top: "44%", left: "58%", width: "55px", rotate: "-25deg", delay: "0.7s" },
  { top: "36%", left: "70%", width: "50px", rotate: "30deg", delay: "0.1s" },
  // Intra-cluster edges (blue)
  { top: "18%", left: "40%", width: "65px", rotate: "8deg", delay: "0.4s" },
  { top: "14%", left: "44%", width: "50px", rotate: "-18deg", delay: "0.6s" },
  // Intra-cluster edges (orange)
  { top: "66%", left: "36%", width: "70px", rotate: "12deg", delay: "0.5s" },
  { top: "62%", left: "42%", width: "50px", rotate: "-20deg", delay: "0.3s" },
  // Cross-cluster edges
  { top: "46%", left: "32%", width: "120px", rotate: "5deg", delay: "0.6s" },
  { top: "26%", left: "30%", width: "90px", rotate: "-8deg", delay: "0.4s" },
  { top: "54%", left: "48%", width: "60px", rotate: "35deg", delay: "0.2s" },
];

const SKEL_BARS = ["64px", "80px", "56px", "48px"];

export function GraphSkeleton({ label = "Loading graph data..." }: { label?: string }) {
  return (
    <div className="relative flex-1 min-h-0 h-full">
      <div className="bg-[#0d1117] absolute inset-0 overflow-hidden">
        {/* Toolbar skeleton */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 flex gap-2 px-3 py-1.5 bg-card/70 rounded-md border border-border z-10">
          {SKEL_BARS.map((w, i) => (
            <div
              key={i}
              className="h-2 rounded-full bg-[#21262d] animate-pulse"
              style={{ width: w, animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>

        {/* Cluster hulls */}
        {SKEL_CLUSTERS.map((c, ci) => (
          <div
            key={`hull-${ci}`}
            className="absolute rounded-[50%] animate-pulse"
            style={{
              left: c.hull.cx,
              top: c.hull.cy,
              width: `calc(${c.hull.rx} * 2)`,
              height: `calc(${c.hull.ry} * 2)`,
              transform: `translate(-50%, -50%) rotate(${c.hull.rotate})`,
              background: `radial-gradient(ellipse at center, rgba(${c.color},0.06) 0%, rgba(${c.color},0.02) 70%, transparent 100%)`,
              border: `1px solid rgba(${c.color},0.08)`,
              animationDelay: `${ci * 0.2}s`,
            }}
          />
        ))}

        {/* Skeleton edges */}
        {SKEL_EDGES.map((e, i) => (
          <div
            key={`e-${i}`}
            className="absolute h-px animate-pulse"
            style={{
              top: e.top,
              left: e.left,
              width: e.width,
              transform: `rotate(${e.rotate})`,
              transformOrigin: "0 0",
              background: "rgba(139,148,158,0.15)",
              animationDelay: e.delay,
            }}
          />
        ))}

        {/* Skeleton nodes */}
        {SKEL_CLUSTERS.map((c, ci) =>
          c.nodes.map((n, ni) => (
            <div
              key={`n-${ci}-${ni}`}
              className="absolute rounded-full animate-pulse"
              style={{
                top: n.top,
                left: n.left,
                width: n.size,
                height: n.size,
                background: `rgba(${c.color},0.25)`,
                boxShadow: `0 0 16px rgba(${c.color},0.15)`,
                animationDelay: n.delay,
              }}
            />
          )),
        )}

        {/* Loading text */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground tracking-wide animate-pulse">
          {label}
        </div>
      </div>
    </div>
  );
}
