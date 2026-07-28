// Standalone demo mode: the app runs entirely on the in-memory demo store,
// auth is a no-op, and no backend is required. Default OFF since T1.58 —
// real auth and the real API are what a fresh checkout gets; set
// VITE_DEMO=1 to opt back into the in-memory fixture.
export const DEMO = import.meta.env.VITE_DEMO === "1"
