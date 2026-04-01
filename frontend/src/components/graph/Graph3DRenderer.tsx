import { useRef, useCallback, useEffect, useMemo } from "react";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { ConvexGeometry } from "three/examples/jsm/geometries/ConvexGeometry.js";
import type { Node3D, GraphData3D } from "@/lib/graph-utils";
import { clusterColor } from "@/lib/graph-colors";

interface Graph3DRendererProps {
  graphData: GraphData3D;
  width: number;
  height: number;
  spacing: number;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
}

export function Graph3DRenderer({
  graphData,
  width,
  height,
  spacing,
  selectedNodeId,
  onNodeSelect,
  onReady,
}: Graph3DRendererProps) {
  const fgRef = useRef<any>(null);
  const hoveredRef = useRef<any>(null);
  const ringRef = useRef<THREE.Mesh | null>(null);
  const hullMeshesRef = useRef<THREE.Mesh[]>([]);

  const neighborSet = useMemo(() => {
    if (!selectedNodeId) return null;
    const ids = new Set<string>();
    ids.add(selectedNodeId);
    for (const link of graphData.links) {
      if (link.hidden) continue;
      const src =
        typeof link.source === "object" ? (link.source as any).id : link.source;
      const tgt =
        typeof link.target === "object" ? (link.target as any).id : link.target;
      if (src === selectedNodeId) ids.add(tgt);
      if (tgt === selectedNodeId) ids.add(src);
    }
    return ids;
  }, [selectedNodeId, graphData.links]);

  const handleNodeHover = useCallback((node: any) => {
    if (hoveredRef.current?.__threeObj) {
      const mat = hoveredRef.current.__threeObj
        .material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.1;
      mat.opacity = 0.9;
    }
    if (node?.__threeObj) {
      const mat = node.__threeObj.material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.5;
      mat.opacity = 1.0;
    }
    hoveredRef.current = node;
    document.body.style.cursor = node ? "pointer" : "default";
  }, []);

  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.d3Force("charge")?.strength(-50);
    fgRef.current.d3Force("link")?.distance(spacing)?.strength(0.7);
    fgRef.current.d3Force("center")?.strength(1.5);
  }, [graphData, spacing]);

  useEffect(() => {
    const scene = fgRef.current?.scene();
    if (ringRef.current && scene) {
      scene.remove(ringRef.current);
      ringRef.current.geometry.dispose();
      (ringRef.current.material as THREE.Material).dispose();
      ringRef.current = null;
    }

    for (const node of graphData.nodes) {
      const obj = (node as any).__threeObj;
      if (!obj) continue;
      const mat = obj.material as THREE.MeshPhongMaterial;
      if (!neighborSet) {
        mat.color.set(node.color);
        mat.emissive.set(node.color);
        mat.emissiveIntensity = 0.1;
        mat.opacity = 0.9;
        obj.scale.set(1, 1, 1);
      } else if (node.id === selectedNodeId) {
        mat.color.set("#ffffff");
        mat.emissive.set("#ffffff");
        mat.emissiveIntensity = 0.6;
        mat.opacity = 1.0;
        obj.scale.set(1.5, 1.5, 1.5);

        if (scene && node.x != null) {
          const radius = (1 + node.val * 1.5) * 2.2;
          const ringGeo = new THREE.TorusGeometry(radius, 0.3, 8, 48);
          const ringMat = new THREE.MeshBasicMaterial({
            color: node.color,
            transparent: true,
            opacity: 0.8,
          });
          const ring = new THREE.Mesh(ringGeo, ringMat);
          ring.position.set(node.x!, node.y!, node.z!);
          scene.add(ring);
          ringRef.current = ring;
        }
      } else if (neighborSet.has(node.id)) {
        mat.color.set(node.color);
        mat.emissive.set(node.color);
        mat.emissiveIntensity = 0.3;
        mat.opacity = 0.9;
        obj.scale.set(1, 1, 1);
      } else {
        mat.color.set(node.color);
        mat.emissive.set(node.color);
        mat.emissiveIntensity = 0.0;
        mat.opacity = 0.15;
        obj.scale.set(1, 1, 1);
      }
    }
  }, [neighborSet, selectedNodeId, graphData.nodes]);

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

    const sampleDirs: THREE.Vector3[] = [];
    const numSamples = 80;
    const goldenRatio = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < numSamples; i++) {
      const theta = Math.acos(1 - (2 * (i + 0.5)) / numSamples);
      const phi = (2 * Math.PI * i) / goldenRatio;
      sampleDirs.push(
        new THREE.Vector3(
          Math.sin(theta) * Math.cos(phi),
          Math.sin(theta) * Math.sin(phi),
          Math.cos(theta),
        ),
      );
    }

    clusterNodes.forEach((nodes) => {
      if (nodes.length < 4) return;

      const centroid = new THREE.Vector3();
      const positions = nodes.map((n) => new THREE.Vector3(n.x!, n.y!, n.z!));
      positions.forEach((p) => centroid.add(p));
      centroid.divideScalar(positions.length);

      const padding = 15;
      const points: THREE.Vector3[] = [];

      for (const dir of sampleDirs) {
        let maxProj = 0;
        for (const p of positions) {
          const proj = p.clone().sub(centroid).dot(dir);
          if (proj > maxProj) maxProj = proj;
        }
        points.push(
          centroid.clone().add(dir.clone().multiplyScalar(maxProj + padding)),
        );
      }

      try {
        const geometry = new ConvexGeometry(points);
        geometry.computeVertexNormals();
        const material = new THREE.MeshPhongMaterial({
          color: clusterColor(nodes[0].cluster),
          transparent: true,
          opacity: 0.06,
          side: THREE.DoubleSide,
          depthWrite: false,
          flatShading: false,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        hullMeshesRef.current.push(mesh);
      } catch {
        // ConvexGeometry can throw if points are coplanar
      }
    });
  }, [graphData]);

  const nodeThreeObject = useCallback((node: Node3D) => {
    const radius = 1 + node.val * 1.5;
    const geometry = new THREE.SphereGeometry(radius, 16, 12);
    const material = new THREE.MeshPhongMaterial({
      color: node.color,
      emissive: node.color,
      emissiveIntensity: 0.1,
      transparent: true,
      opacity: 0.9,
    });
    return new THREE.Mesh(geometry, material);
  }, []);

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={graphData}
      width={width}
      height={height}
      backgroundColor="#0d1117"
      nodeThreeObject={nodeThreeObject}
      nodeLabel={(node: Node3D) => node.content?.slice(0, 100) || ""}
      linkVisibility={(link: any) => !link.hidden}
      linkWidth={(link: any) => {
        if (!neighborSet) return 0.8;
        const src =
          typeof link.source === "object" ? link.source.id : link.source;
        const tgt =
          typeof link.target === "object" ? link.target.id : link.target;
        if (neighborSet.has(src) && neighborSet.has(tgt)) return 2;
        return 0.5;
      }}
      linkColor={(link: any) => {
        if (!neighborSet) return "rgba(76, 201, 240, 0.6)";
        const src =
          typeof link.source === "object" ? link.source.id : link.source;
        const tgt =
          typeof link.target === "object" ? link.target.id : link.target;
        if (neighborSet.has(src) && neighborSet.has(tgt)) return "#4CC9F0";
        return "rgba(76, 201, 240, 0.25)";
      }}
      onNodeClick={(node: Node3D) => {
        onNodeSelect(node.id);
        const distance = 150;
        const h = Math.hypot(node.x!, node.y!, node.z!) || 1;
        const distRatio = 1 + distance / h;
        fgRef.current?.cameraPosition(
          {
            x: node.x! * distRatio,
            y: node.y! * distRatio + distance * 0.4,
            z: node.z! * distRatio,
          },
          { x: node.x, y: node.y, z: node.z },
          1500,
        );
      }}
      onNodeHover={handleNodeHover}
      onBackgroundClick={() => onNodeSelect(null)}
      warmupTicks={80}
      cooldownTicks={150}
      onEngineStop={() => {
        buildClusterHulls();
        onReady();
      }}
    />
  );
}
