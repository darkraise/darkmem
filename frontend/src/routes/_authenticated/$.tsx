import { createFileRoute } from "@tanstack/react-router"
import { AppNotFound } from "@/components/app-chrome"

// Catches every path no other route serves, under the authenticated shell,
// so a signed-in reader's not-found page carries the sidebar and header like
// every other page rather than replacing them (the root's own not-found
// rendered outside the shell for an unknown top-level path).
export const Route = createFileRoute("/_authenticated/$")({
  component: AppNotFound,
})
