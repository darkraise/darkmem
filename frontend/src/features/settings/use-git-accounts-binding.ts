import { useMemo } from "react"
import { DEMO } from "@/lib/demo-flag"
import { useDemoGitAccounts } from "@/demo/hooks"
import {
  useGitAccounts,
  type GitAccountsResponse,
} from "@/hooks/api/use-git-accounts-api"

/** Accounts from the API, or the demo store when there is no backend.
 *
 *  The same gate `use-flags-tab-binding` uses: the query is disabled in demo
 *  mode, so reading it directly would render an empty panel rather than the
 *  fixture. Both arrays are normalised here so every consumer can index them
 *  without a guard — a response that arrives without them is a rendering
 *  crash otherwise, not an empty list.
 */
export function useGitAccountsData(): {
  data: GitAccountsResponse
  isLoading: boolean
} {
  const demo = useDemoGitAccounts()
  const query = useGitAccounts()
  const source = DEMO ? demo : query.data
  const isLoading = DEMO ? false : query.isLoading

  // Memoised because the normalisation would otherwise mint a fresh
  // object on every render, and a consumer that lists it in an effect's
  // dependencies then re-runs that effect forever — which is how the Add
  // repository dialog kept overwriting the operator's account choice.
  return useMemo(
    () => ({
      data: {
        accounts: source?.accounts ?? [],
        providers: source?.providers ?? [],
      },
      isLoading,
    }),
    [source, isLoading],
  )
}
