import type { Meta, StoryObj } from "@storybook/react"
import { SourceBadges } from "./source-badges"

const meta: Meta<typeof SourceBadges> = {
  title: "Chat/SourceBadges",
  component: SourceBadges,
  parameters: { layout: "padded" },
  decorators: [
    (Story) => (
      <div className="bg-background p-4 max-w-lg">
        <Story />
      </div>
    ),
  ],
}
export default meta

type S = StoryObj<typeof SourceBadges>

const singleMemory = [
  {
    id: "m1",
    score: 0.93,
    content: "FastAPI uses dependency injection for auth middleware via Depends()",
    source: "claude-code",
    tags: ["python", "fastapi"],
    created_at: new Date().toISOString(),
  },
]

const manyMemories = Array.from({ length: 5 }, (_, i) => ({
  id: `m${i}`,
  score: 0.95 - i * 0.05,
  content: `Memory result ${i + 1}: relevant context snippet about the queried topic with some additional detail`,
  source: i % 2 === 0 ? "claude-code" : "api",
  tags: ["python", "infra"],
  created_at: new Date(Date.now() - i * 86400000).toISOString(),
}))

const entities = [
  { id: "e1", name: "FastAPI", entity_type: "tool" },
  { id: "e2", name: "OAuth2", entity_type: "concept" },
]

export const Single: S = {
  args: {
    memories: singleMemory,
    entities: [],
  },
}

export const Many: S = {
  args: {
    memories: manyMemories,
    entities,
  },
}

export const EntitiesOnly: S = {
  args: {
    memories: [],
    entities: [
      { id: "e1", name: "PostgreSQL", entity_type: "tool" },
      { id: "e2", name: "Redis", entity_type: "tool" },
      { id: "e3", name: "Docker", entity_type: "tool" },
    ],
  },
}

export const Overflow: S = {
  args: {
    memories: Array.from({ length: 12 }, (_, i) => ({
      id: `m${i}`,
      score: 0.99 - i * 0.02,
      content: `Overflow memory ${i + 1}: this is a longer content string to test wrapping behavior in the expanded panel view`,
      source: "mcp",
      tags: ["overflow", "test"],
      created_at: new Date(Date.now() - i * 3600000).toISOString(),
    })),
    entities: Array.from({ length: 6 }, (_, i) => ({
      id: `e${i}`,
      name: `Entity${i + 1}`,
      entity_type: "concept",
    })),
  },
}
