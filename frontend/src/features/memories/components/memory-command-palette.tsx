import { useState } from "react"
import {
  Command,
  CommandInput,
  CommandList,
  CommandItem,
  CommandEmpty,
} from "darkraise-ui/components/command"

export interface CommandPaletteFilter {
  query: string
  sources: string[]
  types: string[]
  tags: string[]
  technologies: string[]
}

export function parseCommandPaletteQuery(raw: string): CommandPaletteFilter {
  const tokens = raw.split(/\s+/).filter(Boolean)
  const facet: CommandPaletteFilter = {
    query: "",
    sources: [],
    types: [],
    tags: [],
    technologies: [],
  }
  const free: string[] = []
  for (const tok of tokens) {
    const idx = tok.indexOf(":")
    if (idx > 0) {
      const prefix = tok.slice(0, idx)
      const value = tok.slice(idx + 1)
      if (prefix === "source") facet.sources.push(value)
      else if (prefix === "type") facet.types.push(value)
      else if (prefix === "tag") facet.tags.push(value)
      else if (prefix === "tech") facet.technologies.push(value)
      else free.push(tok)
    } else {
      free.push(tok)
    }
  }
  facet.query = free.join(" ")
  return facet
}

export function MemoryCommandPalette({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  onSubmit: (filter: CommandPaletteFilter) => void
}) {
  const [value, setValue] = useState("")

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="w-full max-w-lg bg-popover border border-border rounded-lg shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            onOpenChange(false)
            setValue("")
          }
          if (e.key === "Enter") {
            onSubmit(parseCommandPaletteQuery(value))
            onOpenChange(false)
            setValue("")
          }
        }}
      >
        <Command shouldFilter={false}>
          <CommandInput
            autoFocus
            value={value}
            onValueChange={setValue}
            placeholder="Search memories (source:claude-code tag:python …)"
          />
          <CommandList>
            <CommandEmpty>Press Enter to search.</CommandEmpty>
            <CommandItem
              onSelect={() => {
                onSubmit(parseCommandPaletteQuery(value))
                onOpenChange(false)
                setValue("")
              }}
            >
              Run search
            </CommandItem>
          </CommandList>
        </Command>
      </div>
    </div>
  )
}
