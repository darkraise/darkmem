// Standalone demo mode: the app runs entirely on the in-memory demo store,
// auth is a no-op, and no backend is required. Default OFF since T1.58 —
// real auth and the real API are what a fresh checkout gets; set
// VITE_DEMO=1 to opt back into the in-memory fixture.
//
// Lives outside src/demo/ on purpose (T1.64): this is a permanent, supported
// flag, not migration debt, and every file that only needed this check was
// never really coupled to demo *data* in the first place — relocating it
// removes those files from no-restricted-imports' src/demo/* blast radius
// entirely, rather than needing a glob exception kept in sync by hand.
export const DEMO = import.meta.env.VITE_DEMO === "1"
