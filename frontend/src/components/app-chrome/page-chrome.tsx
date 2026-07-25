import { useEffect } from "react"
import type { ReactNode } from "react"
import type { LucideIcon } from "lucide-react"
import { create } from "zustand"

export interface PageChromeBreadcrumb {
  label: string
  href?: string
}

export interface PageChromeState {
  icon: LucideIcon | null
  title: string
  description: string
  breadcrumbs: PageChromeBreadcrumb[]
  actions: ReactNode
}

const EMPTY: PageChromeState = {
  icon: null,
  title: "",
  description: "",
  breadcrumbs: [],
  actions: null,
}

export const usePageChrome = create<PageChromeState>(() => EMPTY)

export interface PageChromeProps {
  icon?: LucideIcon
  title: string
  description?: string
  breadcrumbs?: PageChromeBreadcrumb[]
  actions?: ReactNode
}

/**
 * Publish this page's identity (icon, title, breadcrumb trail, action
 * buttons) into the app header bar. The set-effect runs after every render
 * on purpose: `actions` is a ReactNode whose click handlers close over the
 * page's latest state, so a deps-guarded effect would leave stale closures
 * in the header.
 */
export function useSetPageChrome({
  icon,
  title,
  description,
  breadcrumbs,
  actions,
}: PageChromeProps) {
  useEffect(() => {
    usePageChrome.setState({
      icon: icon ?? null,
      title,
      description: description ?? "",
      breadcrumbs: breadcrumbs ?? [],
      actions: actions ?? null,
    })
  })
  useEffect(() => () => usePageChrome.setState(EMPTY), [])
}

export function PageChrome(props: PageChromeProps) {
  useSetPageChrome(props)
  return null
}
