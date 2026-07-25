import { useDemoStore } from "./store"

export const useDemoMemories = () => useDemoStore((s) => s.memories)
export const useDemoMemory = (id: string) =>
  useDemoStore((s) => s.memories.find((m) => m.id === id))
export const useDemoRepos = () => useDemoStore((s) => s.repos)
export const useDemoJobs = () => useDemoStore((s) => s.jobs)
export const useDemoLLMProfiles = () => useDemoStore((s) => s.llmProfiles)
export const useDemoStats = () => useDemoStore((s) => s.stats)
export const useDemoEvents = () => useDemoStore((s) => s.events)
export const useDemoContributions = () => useDemoStore((s) => s.contributions)

export const useDemoFacts = () => useDemoStore((s) => s.facts)
export const useDemoFact = (id: string) =>
  useDemoStore((s) => s.facts.find((f) => f.id === id))
export const useDemoArticles = () => useDemoStore((s) => s.articles)
export const useDemoArticle = (id: string) =>
  useDemoStore((s) => s.articles.find((a) => a.id === id))
export const useDemoCommunities = () => useDemoStore((s) => s.communities)
export const useDemoPinSuggestions = () =>
  useDemoStore((s) => s.pinSuggestions)
export const useDemoReviewItems = () => useDemoStore((s) => s.reviewItems)
export const useDemoHygiene = () => useDemoStore((s) => s.hygiene)
export const useDemoLastDetectionRun = () =>
  useDemoStore((s) => s.lastDetectionRun)
