import {
  Braces,
  Database,
  File,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileTerminal,
  FileText,
  FileType,
  Settings2,
  type LucideIcon,
} from "lucide-react"

/** Icon and tint for one file extension.
 *
 * The tint is what makes an explorer scannable -- a column of identical grey
 * glyphs conveys no more than the filenames already do. Colours are Tailwind
 * utility classes rather than raw hex so both themes resolve them; each is a
 * `-500`/`-400` pair chosen to stay legible on the light and dark grounds
 * this app ships.
 */
interface FileIcon {
  icon: LucideIcon
  className: string
}

const CODE = "text-sky-600 dark:text-sky-400"
const DOC = "text-blue-600 dark:text-blue-400"
const DATA = "text-amber-600 dark:text-amber-400"
const SHELL = "text-emerald-600 dark:text-emerald-400"
const CONFIG = "text-violet-600 dark:text-violet-400"
const MEDIA = "text-pink-600 dark:text-pink-400"

const BY_EXTENSION: Record<string, FileIcon> = {
  md: { icon: FileText, className: DOC },
  markdown: { icon: FileText, className: DOC },
  txt: { icon: FileText, className: DOC },
  rst: { icon: FileText, className: DOC },
  pdf: { icon: FileType, className: DOC },

  ts: { icon: FileCode, className: CODE },
  tsx: { icon: FileCode, className: CODE },
  js: { icon: FileCode, className: CODE },
  jsx: { icon: FileCode, className: CODE },
  py: { icon: FileCode, className: CODE },
  cs: { icon: FileCode, className: CODE },
  go: { icon: FileCode, className: CODE },
  rs: { icon: FileCode, className: CODE },
  html: { icon: FileCode, className: CODE },
  css: { icon: FileCode, className: CODE },

  json: { icon: Braces, className: DATA },
  sql: { icon: Database, className: DATA },
  csv: { icon: FileSpreadsheet, className: DATA },

  sh: { icon: FileTerminal, className: SHELL },
  bash: { icon: FileTerminal, className: SHELL },

  yml: { icon: Settings2, className: CONFIG },
  yaml: { icon: Settings2, className: CONFIG },
  toml: { icon: Settings2, className: CONFIG },
  ini: { icon: Settings2, className: CONFIG },
  env: { icon: Settings2, className: CONFIG },

  png: { icon: FileImage, className: MEDIA },
  jpg: { icon: FileImage, className: MEDIA },
  jpeg: { icon: FileImage, className: MEDIA },
  svg: { icon: FileImage, className: MEDIA },
  webp: { icon: FileImage, className: MEDIA },
}

const FALLBACK: FileIcon = { icon: File, className: "text-muted-foreground" }

/**
 * The icon for a leaf row.
 *
 * Keyed on the last dot-segment lowercased. A name with no dot, or one whose
 * extension is not in the table, takes the neutral fallback rather than
 * guessing -- a wrong icon is worse than a plain one, because it is read as
 * information.
 */
export function fileIcon(name: string): FileIcon {
  const dot = name.lastIndexOf(".")
  if (dot <= 0 || dot === name.length - 1) return FALLBACK
  return BY_EXTENSION[name.slice(dot + 1).toLowerCase()] ?? FALLBACK
}
