import { create } from "zustand"
import memoriesData from "./data/memories.json"
import reposData from "./data/repos.json"
import jobsData from "./data/jobs.json"
import llmProfilesData from "./data/llm-profiles.json"
import type { DemoStoreState, Memory, Repo, Job, LlmProfile } from "./types"

const initialMemories = memoriesData as unknown as Memory[]

export const useDemoStore = create<DemoStoreState>((set) => ({
  memories: initialMemories,
  repos: reposData as unknown as Repo[],
  jobs: jobsData as unknown as Job[],
  llmProfiles: llmProfilesData as unknown as LlmProfile[],
  addMemory: (m) => set((s) => ({ memories: [m, ...s.memories] })),
  deleteMemory: (id) => set((s) => ({ memories: s.memories.filter((x) => x.id !== id) })),
  resetMemories: () => set({ memories: initialMemories }),
}))
