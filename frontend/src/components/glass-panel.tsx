import type { ComponentProps } from "react"
import { Card } from "darkraise-ui/components/card"

// Styling only — callers supply width/height/flex/overflow via className so
// the login card (max-w-sm) and the setup wizard (max-h-[90vh] flex-col
// overflow-hidden) each keep their own layout.
// `dm-glass` (globals.css) supplies the base fill + the @supports opaque
// fallback; do not also set a Tailwind bg utility here (it would layer-conflict).
const GLASS =
  "dm-glass rounded-[18px] border border-white/12 shadow-[0_24px_70px_rgba(0,0,0,0.62)] ring-1 ring-indigo-500/10 backdrop-blur-[16px]"

export function GlassPanel({
  className,
  ...props
}: ComponentProps<typeof Card>) {
  return <Card className={`${GLASS} ${className ?? ""}`} {...props} />
}
