/**
 * TanStack Router adapter for darkraise-ui 1.0.8+.
 *
 * darkraise-ui decoupled its layout + navigation components from any specific
 * router in 1.0.8. Every component that used to call TanStack hooks directly
 * now reads them through `useRouterAdapter()`, which the consumer supplies
 * via `RouterAdapterProvider`.
 *
 * This adapter implements the five entry points the UI library expects —
 * `Link`, `useNavigate`, `usePathname`, `useBack`, `useInvalidate` — in terms
 * of `@tanstack/react-router` so the existing nav/sidebar/PageHeader keep
 * working without churn.
 */
import type { CSSProperties, MouseEvent, ReactNode } from "react"
import {
  Link as TanstackLink,
  useLocation as useTanstackLocation,
  useNavigate as useTanstackNavigate,
  useRouter as useTanstackRouter,
} from "@tanstack/react-router"
import type { RouterAdapter, RouterLinkProps } from "darkraise-ui/router"

type LinkProps = {
  to: string
  className?: string
  activeClassName?: string
  activeExact?: boolean
  style?: CSSProperties
  children: ReactNode
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void
}

function AdapterLink({
  to,
  className,
  activeClassName,
  activeExact,
  style,
  children,
  onClick,
}: LinkProps) {
  return (
    <TanstackLink
      to={to}
      className={className}
      activeProps={activeClassName ? { className: activeClassName } : undefined}
      activeOptions={activeExact ? { exact: true } : undefined}
      style={style}
      onClick={onClick}
    >
      {children}
    </TanstackLink>
  )
}

function useAdapterNavigate(): (to: string) => void {
  const navigate = useTanstackNavigate()
  return (to: string) => {
    // Adapter surface accepts a plain path string; delegate to TanStack's
    // object-form navigate so type-safe params still flow through in the app.
    navigate({ to })
  }
}

function useAdapterPathname(): string {
  return useTanstackLocation({ select: (l) => l.pathname })
}

function useAdapterBack(): () => void {
  const router = useTanstackRouter()
  return () => {
    router.history.back()
  }
}

function useAdapterInvalidate(): () => void {
  const router = useTanstackRouter()
  return () => {
    // Fire-and-forget — darkraise-ui's use case is "refresh after nav edit",
    // so awaiting the invalidation promise is not required.
    void router.invalidate()
  }
}

export const tanstackRouterAdapter: RouterAdapter = {
  Link: AdapterLink as RouterAdapter["Link"],
  useNavigate: useAdapterNavigate,
  usePathname: useAdapterPathname,
  useBack: useAdapterBack,
  useInvalidate: useAdapterInvalidate,
}

export type { RouterLinkProps }
