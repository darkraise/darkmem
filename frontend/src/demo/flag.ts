// Standalone demo mode: the app runs entirely on the in-memory demo store,
// auth is a no-op, and no backend is required. Default ON for the skeleton;
// set VITE_DEMO=0 to restore the real auth + API paths.
export const DEMO = import.meta.env.VITE_DEMO !== "0"
