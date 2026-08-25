import { useDemoStore } from "./store"

export const useDemoMemories = () => useDemoStore((s) => s.memories)
export const useDemoMemory = (id: string) =>
  useDemoStore((s) => s.memories.find((m) => m.id === id))
export const useDemoRepos = () => useDemoStore((s) => s.repos)
export const useDemoJobs = () => useDemoStore((s) => s.jobs)
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

export const useDemoGitAccounts = () => useDemoStore((s) => s.gitAccounts)
export const useDemoCodeRepos = () => useDemoStore((s) => s.codeRepos)
export const useDemoCodeRepo = (id: string | undefined) =>
  useDemoStore((s) => s.codeRepos.find((r) => r.id === id))
export const useDemoCodeGraph = (repoId: string | undefined) =>
  useDemoStore((s) => s.codeGraphs.find((g) => g.repo_id === repoId))
export const useDemoMemoryGraph = () => useDemoStore((s) => s.memoryGraph)
export const useDemoChatThreads = () => useDemoStore((s) => s.chatThreads)
export const useDemoChatThread = (id: string | null) =>
  useDemoStore((s) => s.chatThreads.find((t) => t.id === id))

export const useDemoPipelineRuns = () => useDemoStore((s) => s.pipelineRuns)
export const useDemoFeedEvents = () => useDemoStore((s) => s.feedEvents)
export const useDemoPipelineFailures = () =>
  useDemoStore((s) => s.pipelineFailures)
export const useDemoBufferMonitor = () => useDemoStore((s) => s.bufferMonitor)
export const useDemoDreamMonitor = () => useDemoStore((s) => s.dreamMonitor)
export const useDemoDreamCycle = () => useDemoStore((s) => s.dreamCycle)
export const useDemoDreamActions = () => useDemoStore((s) => s.dreamActions)
export const useDemoDreamPastActions = () =>
  useDemoStore((s) => s.dreamPastActions)
export const useDemoDayBuckets = () => useDemoStore((s) => s.dayBuckets)
export const useDemoSessionRuns = () => useDemoStore((s) => s.sessionRuns)

export const useDemoFlags = () => useDemoStore((s) => s.flags)
export const useDemoLLM = () => useDemoStore((s) => s.llm)
export const useDemoSecurity = () => useDemoStore((s) => s.security)
export const useDemoMaintenance = () => useDemoStore((s) => s.maintenance)
export const useDemoDistribution = () => useDemoStore((s) => s.distribution)
