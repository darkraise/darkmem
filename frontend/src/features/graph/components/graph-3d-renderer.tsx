import { useRef, useCallback, useEffect, useMemo } from "react"
import ForceGraph3D from "react-force-graph-3d"
import * as THREE from "three"
import { ConvexGeometry } from "three/examples/jsm/geometries/ConvexGeometry.js"
import type { Node3D, GraphData3D } from "@/features/graph/lib/graph-utils"
import {
  resolveNodeColor,
  resolveGroupColor,
  entityTypeColor,
  memoryEdgeColor,
  relationEdgeColor,
  type MemoryPalette,
} from "@/features/graph/lib/graph-colors"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import { computeHullGroups } from "@/features/graph/lib/graph-geometry"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import { type GraphThemeTokens } from "@/features/graph/lib/code-graph-theme"

interface Graph3DRendererProps {
  graphData: GraphData3D
  width: number
  height: number
  spacing: number
  colorMode: ColorMode
  hullMode: HullMode
  selectedNodeId: string | null
  onNodeSelect: (nodeId: string | null) => void
  onReady: () => void
  tokens: GraphThemeTokens
  palette: MemoryPalette
}

export function Graph3DRenderer({
  graphData,
  width,
  height,
  spacing,
  colorMode,
  hullMode,
  selectedNodeId,
  onNodeSelect,
  onReady,
  tokens,
  palette,
}: Graph3DRendererProps) {
  const fgRef = useRef<any>(null)
  const hoveredRef = useRef<any>(null)
  const ringRef = useRef<THREE.Mesh | null>(null)
  const hullMeshesRef = useRef<THREE.Mesh[]>([])

  const isEntitySelected = selectedNodeId?.startsWith("entity:") ?? false

  const chrome = useMemo(
    () => ({ background: tokens.background, highlight: tokens.foreground }),
    [tokens],
  )

  // Refs so linkColor accessor and buildHulls always read the latest values
  // without those values appearing in their dependency/identity arrays.
  const tokensRef = useRef(tokens)
  tokensRef.current = tokens
  const paletteRef = useRef(palette)
  paletteRef.current = palette

  const colorForNode = (n: Node3D, p: MemoryPalette): string =>
    n.nodeKind === "entity"
      ? entityTypeColor(n.entityType ?? "", p)
      : resolveNodeColor(
          { cluster: n.cluster, memory_type: n.memoryType, tags: n.tags },
          colorMode,
          p,
        )

  const neighborSet = useMemo(() => {
    if (!selectedNodeId) return null
    const ids = new Set<string>()
    ids.add(selectedNodeId)
    for (const link of graphData.links) {
      if (link.hidden && !isEntitySelected) continue
      const src =
        typeof link.source === "object" ? (link.source as any).id : link.source
      const tgt =
        typeof link.target === "object" ? (link.target as any).id : link.target
      if (src === selectedNodeId) ids.add(tgt)
      if (tgt === selectedNodeId) ids.add(src)
    }
    return ids
  }, [selectedNodeId, isEntitySelected, graphData.links])

  const handleNodeHover = useCallback((node: any) => {
    if (hoveredRef.current?.__threeObj) {
      const mat = hoveredRef.current.__threeObj
        .material as THREE.MeshPhongMaterial
      mat.emissiveIntensity = 0.1
      mat.opacity = 0.9
    }
    if (node?.__threeObj) {
      const mat = node.__threeObj.material as THREE.MeshPhongMaterial
      mat.emissiveIntensity = 0.5
      mat.opacity = 1.0
    }
    hoveredRef.current = node
    document.body.style.cursor = node ? "pointer" : "default"
  }, [])

  const prevSpacingRef = useRef(spacing)
  useEffect(() => {
    if (!fgRef.current) return
    fgRef.current.d3Force("charge")?.strength(-50)
    fgRef.current.d3Force("link")?.distance(spacing)?.strength(0.7)
    fgRef.current.d3Force("center")?.strength(1.5)
    if (prevSpacingRef.current !== spacing) {
      prevSpacingRef.current = spacing
      fgRef.current.d3ReheatSimulation()
    }
  }, [graphData, spacing])

  const buildHulls = useCallback(() => {
    const scene = fgRef.current?.scene()
    if (!scene) return

    hullMeshesRef.current.forEach((m) => {
      m.geometry.dispose()
      ;(m.material as THREE.Material).dispose()
      scene.remove(m)
    })
    hullMeshesRef.current = []

    if (hullMode === "none") return

    const memoryNodes = graphData.nodes.filter(
      (n) => n.nodeKind === "memory" && n.x != null,
    )
    const hullGroups = computeHullGroups(memoryNodes, hullMode)

    const sampleDirs: THREE.Vector3[] = []
    const numSamples = 80
    const goldenRatio = (1 + Math.sqrt(5)) / 2
    for (let i = 0; i < numSamples; i++) {
      const theta = Math.acos(1 - (2 * (i + 0.5)) / numSamples)
      const phi = (2 * Math.PI * i) / goldenRatio
      sampleDirs.push(
        new THREE.Vector3(
          Math.sin(theta) * Math.cos(phi),
          Math.sin(theta) * Math.sin(phi),
          Math.cos(theta),
        ),
      )
    }

    const nodeMap = new Map(graphData.nodes.map((n) => [n.id, n]))

    let groupIdx = 0
    for (const [groupKey, memberIds] of hullGroups) {
      const positions: THREE.Vector3[] = []
      for (const id of memberIds) {
        const node = nodeMap.get(id)
        if (node && node.x != null) {
          positions.push(new THREE.Vector3(node.x!, node.y!, node.z!))
        }
      }
      if (positions.length < 4) {
        groupIdx++
        continue
      }

      const centroid = new THREE.Vector3()
      positions.forEach((p) => centroid.add(p))
      centroid.divideScalar(positions.length)

      const padding = 15
      const points: THREE.Vector3[] = []
      for (const dir of sampleDirs) {
        let maxProj = 0
        for (const p of positions) {
          const proj = p.clone().sub(centroid).dot(dir)
          if (proj > maxProj) maxProj = proj
        }
        points.push(
          centroid.clone().add(dir.clone().multiplyScalar(maxProj + padding)),
        )
      }

      try {
        const geometry = new ConvexGeometry(points)
        geometry.computeVertexNormals()
        // paletteRef keeps buildHulls deps stable ([graphData, colorMode, hullMode])
        // while always reading the latest palette when hulls are rebuilt on a theme flip.
        const hullColor = resolveGroupColor(
          groupKey,
          groupIdx,
          colorMode,
          hullMode,
          paletteRef.current,
        )
        const material = new THREE.MeshPhongMaterial({
          color: hullColor,
          transparent: true,
          opacity: 0.06,
          side: THREE.DoubleSide,
          depthWrite: false,
          flatShading: false,
        })
        const mesh = new THREE.Mesh(geometry, material)
        scene.add(mesh)
        hullMeshesRef.current.push(mesh)
      } catch {
        // ConvexGeometry can throw if points are coplanar
      }
      groupIdx++
    }
  }, [graphData, colorMode, hullMode])

  // Recolor node materials and hull meshes in place on a theme or colorMode change.
  // Updating materials directly (not node positions) preserves the settled 3D layout.
  useEffect(() => {
    for (const node of graphData.nodes) {
      const color = colorForNode(node, palette)
      node.color = color
      const obj = (node as any).__threeObj
      if (!obj) continue
      const mat = obj.material as THREE.MeshPhongMaterial
      mat.color.set(color)
      mat.emissive.set(color)
    }
    buildHulls()
    fgRef.current?.refresh?.()
    // palette intentionally excluded from deps: the renderer recolors node
    // materials in place so a theme flip preserves 3D positions. colorMode (a dep)
    // still recomputes with the current palette.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [`${tokens.background}:${tokens.isDark}:${colorMode}`])

  // Declared after the recolor effect so passive effects run recolor-first:
  // the recolor effect refreshes node.color/base materials, then this effect
  // rebuilds the selection ring from the fresh color and re-applies the
  // highlight to the selected node — keeping the ring in sync across a theme flip.
  useEffect(() => {
    const scene = fgRef.current?.scene()
    if (ringRef.current && scene) {
      scene.remove(ringRef.current)
      ringRef.current.geometry.dispose()
      ;(ringRef.current.material as THREE.Material).dispose()
      ringRef.current = null
    }

    for (const node of graphData.nodes) {
      const obj = (node as any).__threeObj
      if (!obj) continue
      const mat = obj.material as THREE.MeshPhongMaterial
      if (!neighborSet) {
        mat.color.set(node.color)
        mat.emissive.set(node.color)
        mat.emissiveIntensity = 0.1
        mat.opacity = 0.9
        obj.scale.set(1, 1, 1)
      } else if (node.id === selectedNodeId) {
        mat.color.set(chrome.highlight)
        mat.emissive.set(chrome.highlight)
        mat.emissiveIntensity = 0.6
        mat.opacity = 1.0
        obj.scale.set(1.5, 1.5, 1.5)

        if (scene && node.x != null) {
          const radius = (1 + node.val * 1.5) * 2.2
          const ringGeo = new THREE.TorusGeometry(radius, 0.3, 8, 48)
          const ringMat = new THREE.MeshBasicMaterial({
            color: node.color,
            transparent: true,
            opacity: 0.8,
          })
          const ring = new THREE.Mesh(ringGeo, ringMat)
          ring.position.set(node.x!, node.y!, node.z!)
          scene.add(ring)
          ringRef.current = ring
        }
      } else if (neighborSet.has(node.id)) {
        mat.color.set(node.color)
        mat.emissive.set(node.color)
        mat.emissiveIntensity = 0.3
        mat.opacity = 0.9
        obj.scale.set(1, 1, 1)
      } else {
        mat.color.set(node.color)
        mat.emissive.set(node.color)
        mat.emissiveIntensity = 0.0
        mat.opacity = 0.15
        obj.scale.set(1, 1, 1)
      }
    }
  }, [neighborSet, selectedNodeId, graphData.nodes, chrome])

  useEffect(() => {
    return () => {
      document.body.style.cursor = "default"
      const scene = fgRef.current?.scene()
      if (ringRef.current) {
        scene?.remove(ringRef.current)
        ringRef.current.geometry.dispose()
        ;(ringRef.current.material as THREE.Material).dispose()
        ringRef.current = null
      }
      for (const m of hullMeshesRef.current) {
        scene?.remove(m)
        m.geometry.dispose()
        ;(m.material as THREE.Material).dispose()
      }
      hullMeshesRef.current = []
    }
  }, [])

  const nodeThreeObject = useCallback((node: Node3D) => {
    const radius = 1 + node.val * 1.5
    const geometry =
      node.nodeKind === "entity"
        ? new THREE.OctahedronGeometry(radius * 0.6)
        : new THREE.SphereGeometry(radius, 16, 12)
    const color = colorForNode(node, palette)
    const material = new THREE.MeshPhongMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.1,
      transparent: true,
      opacity: 0.9,
    })
    return new THREE.Mesh(geometry, material)
    // Empty deps keep node-object identity stable (the graph library would
    // recreate every node if this changed); the recolor effect owns later
    // color updates, so the stale palette/colorMode captured here is intended.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={graphData}
      width={width}
      height={height}
      backgroundColor={chrome.background}
      nodeThreeObject={nodeThreeObject}
      nodeLabel={(node: Node3D) =>
        node.nodeKind === "entity"
          ? (node.entityName ?? "")
          : node.content?.slice(0, 100) || ""
      }
      linkVisibility={(link: any) =>
        !link.hidden && link.linkKind !== "membership"
      }
      linkWidth={(link: any) => {
        if (!neighborSet) {
          if (link.linkKind === "relation") return 1.5
          return 0.8
        }
        const src =
          typeof link.source === "object" ? link.source.id : link.source
        const tgt =
          typeof link.target === "object" ? link.target.id : link.target
        if (neighborSet.has(src) && neighborSet.has(tgt)) return 2
        if (link.linkKind === "relation") return 1.5
        return 0.5
      }}
      linkColor={(link: any) => {
        if (!neighborSet) {
          if (link.linkKind === "relation")
            return relationEdgeColor(tokensRef.current)
          return memoryEdgeColor(tokensRef.current.primary, tokensRef.current)
        }
        const src =
          typeof link.source === "object" ? link.source.id : link.source
        const tgt =
          typeof link.target === "object" ? link.target.id : link.target
        if (neighborSet.has(src) && neighborSet.has(tgt)) {
          if (link.linkKind === "relation")
            return relationEdgeColor(tokensRef.current)
          return tokensRef.current.primary
        }
        if (link.linkKind === "relation")
          return relationEdgeColor(tokensRef.current)
        return memoryEdgeColor(tokensRef.current.primary, tokensRef.current)
      }}
      linkDirectionalArrowLength={(link: any) =>
        link.linkKind === "relation" ? 4 : 0
      }
      linkDirectionalArrowRelPos={1}
      onNodeClick={(node: Node3D) => {
        onNodeSelect(node.id)
        const distance = 150
        const h = Math.hypot(node.x!, node.y!, node.z!) || 1
        const distRatio = 1 + distance / h
        fgRef.current?.cameraPosition(
          {
            x: node.x! * distRatio,
            y: node.y! * distRatio + distance * 0.4,
            z: node.z! * distRatio,
          },
          { x: node.x, y: node.y, z: node.z },
          1500,
        )
      }}
      onNodeHover={handleNodeHover}
      onBackgroundClick={() => onNodeSelect(null)}
      warmupTicks={80}
      cooldownTicks={150}
      onEngineStop={() => {
        buildHulls()
        onReady()
      }}
    />
  )
}
