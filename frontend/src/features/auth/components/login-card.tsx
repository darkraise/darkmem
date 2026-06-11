import { GlassPanel } from "@/components/glass-panel"
import { LoginForm } from "./login-form"

function BrandGlyph() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <g stroke="#67e8f9" strokeWidth="1.6" fill="none">
        <line x1="6" y1="7" x2="14" y2="5" />
        <line x1="6" y1="7" x2="9" y2="17" />
        <line x1="14" y1="5" x2="18" y2="14" />
        <line x1="9" y1="17" x2="18" y2="14" />
      </g>
      <g fill="#818cf8">
        <circle cx="6" cy="7" r="2.4" />
        <circle cx="14" cy="5" r="2.4" />
        <circle cx="18" cy="14" r="2.4" />
        <circle cx="9" cy="17" r="2.4" />
      </g>
    </svg>
  )
}

export function LoginCard({ onSuccess }: { onSuccess: () => void }) {
  return (
    <GlassPanel className="w-full max-w-sm p-8">
      <div className="mb-1 flex items-center justify-center gap-2.5">
        <BrandGlyph />
        <span className="bg-gradient-to-r from-[#c7d2fe] via-[#a5b4fc] to-[#67e8f9] bg-clip-text text-3xl font-extrabold tracking-[0.3px] text-transparent">
          darkmem
        </span>
      </div>
      <p className="text-muted-foreground mb-6 text-center text-sm">
        Sign in to continue
      </p>
      <LoginForm onSuccess={onSuccess} />
    </GlassPanel>
  )
}
