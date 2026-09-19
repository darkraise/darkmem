import { Card, CardContent } from "darkraise-ui/components/card"
import { LoginForm } from "./login-form"

export function LoginCard({ onSuccess }: { onSuccess: () => void }) {
  return (
    <Card className="w-full max-w-sm">
      <CardContent className="p-8">
        <div className="mb-1 flex items-center justify-center gap-2.5">
          <span aria-hidden className="dm-brand-mark size-7" />
          <span className="text-foreground text-3xl font-extrabold tracking-tight">
            darkmem
          </span>
        </div>
        <p className="text-muted-foreground mb-6 text-center text-sm">
          Sign in to continue
        </p>
        <LoginForm onSuccess={onSuccess} />
      </CardContent>
    </Card>
  )
}
