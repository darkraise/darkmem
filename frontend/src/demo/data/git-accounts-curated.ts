import type { DemoGitAccountsState } from "../types"

// S25 — Git accounts. Two GitHub credentials on the same host so the panel
// renders both the default badge and a non-default row, plus an Enterprise
// account carrying its own default (the partial unique index is scoped to
// provider *and* host, and the demo should show that rather than imply one
// default exists globally).
export const CURATED_GIT_ACCOUNTS: DemoGitAccountsState = {
  accounts: [
    {
      id: "3f7c1e02-1a41-4a90-9a6d-1c0f5b2a7d11",
      label: "Personal",
      provider: "github",
      host: "github.com",
      username: "darkraise",
      token_hint: "4f2a",
      scopes: "repo, read:org",
      is_default: true,
      last_verified_at: "2026-08-19T09:12:00Z",
      repo_count: 4,
      created_at: "2026-06-02T10:00:00Z",
      updated_at: "2026-08-19T09:12:00Z",
    },
    {
      id: "8b2d4c60-77f3-4bd1-9c2e-5a0e91b3c422",
      label: "OSS bot",
      provider: "github",
      host: "github.com",
      username: "darkmem-bot",
      // A fine-grained PAT: GitHub sends no X-OAuth-Scopes header for these,
      // so a null here is the normal case, not a failed verification.
      token_hint: "9c1b",
      scopes: null,
      is_default: false,
      last_verified_at: "2026-08-21T14:40:00Z",
      repo_count: 1,
      created_at: "2026-07-14T08:30:00Z",
      updated_at: "2026-08-21T14:40:00Z",
    },
    {
      id: "c41a9e77-2b58-4f03-8e77-6d4a2f9b0e33",
      label: "Work",
      provider: "github",
      host: "git.internal.example",
      username: "d.raise",
      token_hint: "7e60",
      scopes: "repo",
      is_default: true,
      last_verified_at: "2026-08-11T16:05:00Z",
      repo_count: 0,
      created_at: "2026-08-11T16:05:00Z",
      updated_at: "2026-08-11T16:05:00Z",
    },
  ],
  providers: [
    { provider: "github", label: "GitHub", default_host: "github.com" },
    { provider: "gitlab", label: "GitLab", default_host: "gitlab.com" },
  ],
}
