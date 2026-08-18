import { createFileRoute } from "@tanstack/react-router"
import { JobsPage } from "@/features/jobs/components/jobs-page"

export const Route = createFileRoute("/_authenticated/jobs")({
  component: JobsPage,
})
