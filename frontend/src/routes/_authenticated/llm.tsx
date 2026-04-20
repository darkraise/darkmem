import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/_authenticated/llm")({
  beforeLoad: () => {
    throw redirect({ to: "/pipeline" })
  },
})
