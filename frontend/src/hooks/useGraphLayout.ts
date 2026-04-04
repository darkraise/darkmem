import { useState } from "react";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { SizeMode } from "@/lib/graph-utils";
import type { HullMode } from "@/lib/graph-geometry";

export function useGraphLayout() {
  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");
  const [nodeSpacing, setNodeSpacing] = useState(100);
  const [clusterTightness, setClusterTightness] = useState(300);
  const [hullMode, setHullMode] = useState<HullMode>("none");
  const [spacing3D, setSpacing3D] = useState(50);

  const debouncedTightness = useDebouncedValue(clusterTightness, 500);
  const debouncedSpacing2D = useDebouncedValue(nodeSpacing, 500);

  return {
    sizeMode,
    setSizeMode,
    nodeSpacing,
    setNodeSpacing,
    clusterTightness,
    setClusterTightness,
    hullMode,
    setHullMode,
    spacing3D,
    setSpacing3D,
    debouncedTightness,
    debouncedSpacing2D,
  };
}
