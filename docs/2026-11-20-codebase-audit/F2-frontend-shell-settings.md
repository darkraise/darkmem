# F2 — frontend shell, settings and operations features

Reviewer findings for the 2026-11-20 audit, as returned. Summary first where the reviewer gave one, then one entry per finding. Index and verification status: `docs/2026-11-20-codebase-audit.md`.

**High**
1. **LLM saves always say "Saved".** `features/settings/use-llm-tab-binding.ts:195-202` shows the toast without waiting for the request. Nothing anywhere catches the error, so a refused save (e.g. pointing a purpose at the verification-judge provider) is reported as saved.

**Medium**
2. **Maintenance re-embed count goes stale.** `use-maintenance-tab-binding.ts:53` stores the count under a different cache name than the one the WebSocket and the LLM save refresh. After an embedder change it can still show 0. Fix: use the existing shared hooks instead of its private copies.
3. **WebSocket never signs out.** `lib/websocket.ts:262-267` ignores the server's "session expired" close and retries every 30s forever. An idle tab goes silently stale instead of returning to sign-in.
4. **Demo mode still calls the API** from Settings → LLM: `useLlmProviders`, the model probe, `useSystemPrompts`. On the dev proxy that reaches production, gets a 401 and throws the demo to `/login`.
5. **Settings has five save models** (detail below), three ways of showing a load failure, and three confirmation styles.
6. **LLM tab invents values on load failure.** `use-llm-tab-binding.ts:172-188` shows blank models and a fixture judge `qwen2.5:3b` as if real.
7. **Flags dialogs drop edits on refusal.** They close on Save before the write lands (`flags-tab.tsx:629` and four more sites); the edits are lost and only a toast remains.

The five save models:
- **Flags:** edit in a dialog, which closes immediately; errors only as a toast.
- **LLM:** edit in a dialog, "Saved" toast with no error path.
- **Git accounts, providers, system prompt:** dialog stays open until the save succeeds.
- **Notifications, research, job history:** inline form with a Save button.
- **Distribution, research arm:** save on blur or on toggle.

**Low**
8. Number fields in the Flags dialogs only commit on blur while Save is disabled until something changes, so Save may never enable (plausible; needs a browser check). One field type clamps out-of-range values silently, the other shows an error.
9. The app never calls `/auth/refresh`, so every session ends hard after 24h with a full-page reload. There is no token-refresh race because there is no refresh.
10. About 18 exported hooks in `hooks/api` have no production importer (for example `useReprocessStream`, `useHealth`, the re-embed hooks, the graph hooks), plus WebSocket cache writes and refreshes that nothing reads.
11. Unused auth code: `useSession`, `useLogout`, `LogoutButton`, `authAdapter.me`, `lib/api.ts login()`. `useSession` would also loop forever under zustand 5 if anyone used it.
12. `lib/form-resolvers.ts` and `lib/source-colors.ts` are imported only by their tests; `hooks/useApi.ts` by nothing. `keepDialogOpenOnListEscape` (7 call sites) is retirable by its own comment, which I didn't verify against its test.
13. `formatDateTime` is defined four times. Both `formatDuration` copies print "1m 60s" for 119.6 seconds.
14. `checkSetupStatus` (`lib/api.ts:213`) ignores the HTTP status, so a server error makes an initialized instance show the setup wizard.
15. The setup wizard keeps vendor API keys in localStorage until setup finishes (`setupWizardStore.ts:196`).
16. The Research tab overwrites typed budgets on every reload of its settings (`research-tab.tsx:51`).
17. In development only, StrictMode leaves a duplicate WebSocket, so every event toasts twice.
18. Minor performance and robustness items: queries don't pass cancellation signals; the maintenance tab polls `/jobs` every 5s to read one value; the project switcher shows "No project holds anything yet" when loading fails.

**Checked and sound:** the 401-burst guard and redirect logic, error normalisation, the route guards and safe redirect, the unauthenticated theme load, polling gated off in demo, inactive tabs not mounting, route code splitting, every dependency being imported, and the other demo guards.

**Not covered:** backups and security tabs, setup step components, activity, dashboard and usage components, most app-chrome, `src/demo`, and the tsconfig files.
