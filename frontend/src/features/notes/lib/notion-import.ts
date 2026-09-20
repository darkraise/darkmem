import { apiUpload } from "@/lib/api"

export type ImportWarning = {
  path: string | null
  kind: string
  detail: string
}

export type ImportReport = {
  root_page_id: string
  pages_created: number
  databases: number
  attachments_stored: number
  attachment_bytes: number
  warnings: ImportWarning[]
  warnings_omitted: number
}

export function importNotionExport(
  project: string,
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<ImportReport> {
  return apiUpload<ImportReport>(
    `/pages/import/notion?project=${encodeURIComponent(project)}`,
    file,
    { headers: { "Content-Type": "application/zip" }, onProgress },
  )
}
