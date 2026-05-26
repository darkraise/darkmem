// Run with: tsx src/demo/data/generate.ts > src/demo/data/memories.json
import { randomUUID } from "node:crypto"

const SOURCES = ["claude-code", "mcp-test", "api", "rest-test", "dashboard"] as const
const TYPES = ["fact", "decision", "preference", "reference", "context"] as const
const TECHS = [
  "python", "fastapi", "postgres", "react", "typescript", "vite",
  "pytest", "alembic", "docker", "kubernetes", "qdrant", "redis",
]
const TAGS = [
  "auth", "pipeline", "infra", "ui", "backend", "memory",
  "embedding", "classification", "extraction", "retrieval",
]

const rows = Array.from({ length: 5000 }, (_, i) => ({
  id: randomUUID(),
  content: `Demo memory ${i}: ${TECHS[i % TECHS.length]} setup for ${TAGS[i % TAGS.length]}`,
  source: SOURCES[i % SOURCES.length],
  memory_type: TYPES[i % TYPES.length],
  technologies: [TECHS[i % TECHS.length], TECHS[(i + 3) % TECHS.length]],
  tags: [TAGS[i % TAGS.length], TAGS[(i + 2) % TAGS.length]],
  project: "default",
  confidence: 0.5 + ((i * 17) % 100) / 200,
  status: "active",
  created_at: new Date(Date.now() - i * 60_000).toISOString(),
}))

console.log(JSON.stringify(rows, null, 2))
