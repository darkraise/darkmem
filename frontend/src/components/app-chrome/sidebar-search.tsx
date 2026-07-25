import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "darkraise-ui/components/command"
import { Kbd } from "darkraise-ui/components/kbd"
import type { NavGroup, NavItem } from "darkraise-ui/layout"
import { splitNavHref } from "@/providers/router-adapter"

interface FlatNavEntry {
  label: string
  href: string
}

function flattenNav(nav: NavGroup[]): FlatNavEntry[] {
  const out: FlatNavEntry[] = []
  const push = (item: NavItem, parentLabel?: string) => {
    if (item.children && item.children.length > 0) {
      for (const child of item.children) push(child, item.label)
      return
    }
    out.push({
      label:
        parentLabel && parentLabel !== item.label
          ? `${parentLabel} · ${item.label}`
          : item.label,
      href: item.href,
    })
  }
  for (const group of nav) {
    for (const item of group.items) push(item, group.label)
  }
  return out
}

/**
 * Sidebar-resident search trigger + command palette. The layout's built-in
 * header SearchCommand cannot be unmounted (LayoutHeader hardcodes it when
 * no children are passed), so in the sidebar layout its trigger is hidden
 * via CSS and its Ctrl+K binding is pre-empted here with a capture-phase
 * listener + stopImmediatePropagation — otherwise both palettes would open.
 */
export function SidebarSearch({ nav }: { nav: NavGroup[] }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const items = useMemo(() => flattenNav(nav), [nav])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        e.stopImmediatePropagation()
        setOpen((prev) => !prev)
      }
    }
    window.addEventListener("keydown", onKeyDown, { capture: true })
    return () =>
      window.removeEventListener("keydown", onKeyDown, { capture: true })
  }, [])

  return (
    <>
      <Button
        variant="outline"
        className="dr-search-command-trigger w-full"
        onClick={() => setOpen(true)}
      >
        <Search aria-hidden className="h-4 w-4 shrink-0" />
        <span className="dm-sidebar-search-label">Search...</span>
        <Kbd size="sm" className="dm-sidebar-search-kbd ml-auto">
          Ctrl K
        </Kbd>
      </Button>
      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Search"
        description="Jump to a page"
      >
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Navigation">
            {items.map((item) => (
              <CommandItem
                key={item.href}
                onSelect={() => {
                  const target = splitNavHref(item.href)
                  void navigate({ to: target.to, search: target.search })
                  setOpen(false)
                }}
              >
                {item.label}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  )
}
