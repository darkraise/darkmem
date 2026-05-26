import { useDemoStore } from "./store"

export const useDemoMemories = () => useDemoStore((s) => s.memories)
export const useDemoRepos = () => useDemoStore((s) => s.repos)
export const useDemoJobs = () => useDemoStore((s) => s.jobs)
export const useDemoLLMProfiles = () => useDemoStore((s) => s.llmProfiles)
