import { useRef, useCallback, useEffect } from "react";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { ConvexGeometry } from "three/examples/jsm/geometries/ConvexGeometry.js";
import type { Node3D, Link3D, GraphData3D } from "@/lib/graph-utils";

interface ForceGraph3DWrapperProps {
  graphData: GraphData3D;
  width: number;
  height: number;
  spacing: number;
  selectedNodeId: string | null;
  onNodeSelect: (node: Node3D | null) => void;
}

export function ForceGraph3DWrapper({
  graphData,
  width,
  height,
  spacing,
  selectedNodeId,
  onNodeSelect,
}: ForceGraph3DWrapperProps) {
  const fgRef = useRef<any>(null);
  const hoveredRef = useRef<Node3D | null>(null);
  const selectedRef = useRef<Node3D | null>(null);
  const hullMeshesRef = useRef<THREE.Mesh[]>([]);
  const clickTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.d3Force("charge")?.strength(-120);
    fgRef.current.d3Force("link")?.distance(spacing);
  }, [graphData, spacing]);

  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.d3Force("link")?.distance(spacing);
    fgRef.current.d3ReheatSimulation();
  }, [spacing]);

  useEffect(() => {
    if ((selectedRef.current as any)?.__threeObj) {
      const mat = (selectedRef.current as any).__threeObj
        .material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.1;
    }
    const newSel = graphData.nodes.find((n) => n.id === selectedNodeId);
    if ((newSel as any)?.__threeObj) {
      const mat = (newSel as any).__threeObj
        .material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.6;
    }
    selectedRef.current = newSel ?? null;
  }, [selectedNodeId, graphData.nodes]);

  const buildClusterHulls = useCallback(() => {
    const scene = fgRef.current?.scene();
    if (!scene) return;

    hullMeshesRef.current.forEach((m) => {
      m.geometry.dispose();
      (m.material as THREE.Material).dispose();
      scene.remove(m);
    });
    hullMeshesRef.current = [];

    const clusterNodes = new Map<number, Node3D[]>();
    for (const node of graphData.nodes) {
      if (node.cluster >= 0 && node.x != null) {
        const group = clusterNodes.get(node.cluster) ?? [];
        group.push(node);
        clusterNodes.set(node.cluster, group);
      }
    }

    clusterNodes.forEach((nodes) => {
      if (nodes.length < 4) return;
      const points = nodes.map(
        (n) => new THREE.Vector3(n.x!, n.y!, n.z!),
      );
      try {
        const geometry = new ConvexGeometry(points);
        const material = new THREE.MeshPhongMaterial({
          color: nodes[0].color,
          transparent: true,
          opacity: 0.08,
          side: THREE.DoubleSide,
          depthWrite: false,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        hullMeshesRef.current.push(mesh);
      } catch {
        // ConvexGeometry can throw if points are coplanar
      }
    });
  }, [graphData]);

  const handleNodeClick = useCallback(
    (node: Node3D) => {
      if (clickTimerRef.current) {
        clearTimeout(clickTimerRef.current);
        clickTimerRef.current = null;
        const distance = 80;
        const distRatio =
          1 + distance / Math.hypot(node.x!, node.y!, node.z!);
        fgRef.current?.cameraPosition(
          {
            x: node.x! * distRatio,
            y: node.y! * distRatio,
            z: node.z! * distRatio,
          },
          node,
          2000,
        );
      } else {
        clickTimerRef.current = window.setTimeout(() => {
          clickTimerRef.current = null;
          onNodeSelect(node);
        }, 300);
      }
    },
    [onNodeSelect],
  );

  const handleNodeHover = useCallback((node: Node3D | null) => {
    const prev = hoveredRef.current;
    if ((prev as any)?.__threeObj) {
      const mat = (prev as any).__threeObj.material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.1;
    }
    if ((node as any)?.__threeObj) {
      const mat = (node as any).__threeObj.material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.4;
    }
    hoveredRef.current = node;
  }, []);

  const nodeThreeObject = useCallback((node: Node3D) => {
    const geometry = new THREE.SphereGeometry(node.val, 16, 12);
    const material = new THREE.MeshPhongMaterial({
      color: node.color,
      emissive: node.color,
      emissiveIntensity: 0.1,
      transparent: true,
      opacity: 0.9,
    });
    return new THREE.Mesh(geometry, material);
  }, []);

  const linkColor = useCallback(
    (link: Link3D) =>
      `rgba(76, 201, 240, ${(0.15 + link.score * 0.6).toFixed(2)})`,
    [],
  );

  const nodeLabel = useCallback(
    (node: Node3D) =>
      `<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 12px;max-width:300px;color:#c9d1d9;font-size:12px;">${node.content.slice(0, 150)}${node.content.length > 150 ? "…" : ""}</div>`,
    [],
  );

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={graphData}
      width={width}
      height={height}
      backgroundColor="#0d1117"
      nodeThreeObject={nodeThreeObject}
      nodeThreeObjectExtend={false}
      nodeLabel={nodeLabel}
      linkColor={linkColor}
      linkWidth={0.3}
      linkOpacity={0.6}
      onNodeClick={handleNodeClick}
      onNodeHover={handleNodeHover}
      onNodeDragEnd={(node: Node3D) => {
        node.fx = node.x;
        node.fy = node.y;
        node.fz = node.z;
      }}
      onEngineStop={buildClusterHulls}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.3}
      warmupTicks={100}
      cooldownTicks={200}
      controlType="orbit"
    />
  );
}
