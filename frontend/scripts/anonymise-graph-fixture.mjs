import { createHash } from "node:crypto"
import { readFileSync, writeFileSync } from "node:fs"

const [inPath, outPath] = process.argv.slice(2)
if (!inPath || !outPath) {
  console.error("usage: anonymise-graph-fixture.mjs <in.json> <out.json>")
  process.exit(1)
}

const hash = (id) => createHash("sha256").update(String(id)).digest("hex").slice(0, 12)
const input = JSON.parse(readFileSync(inPath, "utf8"))

const memoryIds = new Map()
const memories = input.memories.map((m) => {
  const id = hash(m.id)
  memoryIds.set(m.id, id)
  return { id, cluster: m.cluster, memory_type: m.memory_type, importance: m.importance }
})

const edges = (input.similarity_edges ?? [])
  .filter((e) => memoryIds.has(e.source) && memoryIds.has(e.target))
  .map((e) => ({
    source: memoryIds.get(e.source),
    target: memoryIds.get(e.target),
    score: Math.round(e.score * 1000) / 1000,
  }))

const clusterNames = Object.fromEntries(
  Object.keys(input.cluster_names ?? {}).map((k) => [k, `Cluster ${k}`]),
)

const out = { memories, edges, clusterNames }

if (Array.isArray(input.entities)) {
  const entityIds = new Map()
  out.entities = []
  input.entities.forEach((e, i) => {
    const linked = (e.memory_ids ?? []).filter((id) => memoryIds.has(id)).map((id) => memoryIds.get(id))
    if (linked.length === 0) return
    const id = hash(e.id)
    entityIds.set(e.id, id)
    out.entities.push({ id, name: `Entity ${i + 1}`, entity_type: e.entity_type, memory_ids: linked })
  })
  out.entityRelations = (input.entity_relations ?? [])
    .filter((r) => entityIds.has(r.source) && entityIds.has(r.target))
    .map((r) => ({
      source: entityIds.get(r.source),
      target: entityIds.get(r.target),
      type: r.type,
      weight: r.weight,
    }))
}

writeFileSync(outPath, JSON.stringify(out))
