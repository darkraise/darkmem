import { create } from "zustand"
import memoriesData from "./data/memories.json"
import reposData from "./data/repos.json"
import jobsData from "./data/jobs.json"
import llmProfilesData from "./data/llm-profiles.json"
import {
  buildActivityFeed,
  buildContributions,
  buildDashboardStats,
} from "./dashboard"
import type { DemoStoreState, Memory, Repo, Job, LlmProfile } from "./types"

const initialMemories = memoriesData as unknown as Memory[]

export const useDemoStore = create<DemoStoreState>((set) => ({
  memories: initialMemories,
  repos: reposData as unknown as Repo[],
  jobs: jobsData as unknown as Job[],
  llmProfiles: llmProfilesData as unknown as LlmProfile[],
  stats: buildDashboardStats(initialMemories.length),
  events: buildActivityFeed(),
  contributions: buildContributions(),
  addMemory: (m) =>
    set((s) => ({
      memories: [m, ...s.memories],
      stats: { ...s.stats, totalMemories: s.memories.length + 1 },
    })),
  deleteMemory: (id) =>
    set((s) => {
      const memories = s.memories.filter((x) => x.id !== id)
      return {
        memories,
        stats: { ...s.stats, totalMemories: memories.length },
      }
    }),
  resetMemories: () =>
    set((s) => ({
      memories: initialMemories,
      stats: { ...s.stats, totalMemories: initialMemories.length },
    })),
}))
