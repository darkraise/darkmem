import { useDemoStore } from "./store"

export const useDemoMemories = () => useDemoStore((s) => s.memories)
export const useDemoRepos = () => useDemoStore((s) => s.repos)
export const useDemoJobs = () => useDemoStore((s) => s.jobs)
export const useDemoLLMProfiles = () => useDemoStore((s) => s.llmProfiles)
export const useDemoStats = () => useDemoStore((s) => s.stats)
export const useDemoEvents = () => useDemoStore((s) => s.events)
export const useDemoContributions = () => useDemoStore((s) => s.contributions)
