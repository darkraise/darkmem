/**
 * Named re-exports of specific fixture constants for the handful of
 * production files that need one narrow value from `src/demo/data/*`
 * without reaching into that path directly (T1.64: the `no-restricted-imports`
 * rule's error-severity target is `src/demo/data/**` specifically, and this
 * file is the sanctioned indirection — a pure re-export, zero behavior
 * change, mirroring how `hooks.ts` indirects the store).
 */
export { DAY_DRILL_DEFAULT } from "./data/activity-curated"
export { CURATED_CHAT_THREADS } from "./data/chat-curated"
export {
  SETUP_API_KINDS,
  SETUP_BASE_PATH,
  SETUP_CRUMBS,
  SETUP_DIRS,
  type SetupKindFixture,
} from "./data/settings-curated"
