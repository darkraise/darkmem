import type { ComponentProps } from "react"
import { Eye, EyeOff } from "lucide-react"
import {
  PasswordInput,
  PasswordInputControl,
  PasswordInputField,
  PasswordInputIndicator,
  PasswordInputVisibilityTrigger,
} from "darkraise-ui/components/password-input"

/** The login card's brand block (accent-coloured mark + `text-foreground`
 *  wordmark), shared by both setup wizards. The wizard used to paint a fixed
 *  indigo-to-cyan gradient wordmark that ignored the accent picker and the
 *  light theme, so the first screen an operator sees diverged from the second. */
export function SetupBrand({
  subtitle = "Initial setup",
}: {
  subtitle?: string
}) {
  return (
    <div className="flex shrink-0 flex-col items-center gap-1">
      <div className="flex items-center justify-center gap-2.5">
        <span aria-hidden className="dm-brand-mark size-7" />
        <h1 className="text-foreground text-3xl font-extrabold tracking-tight">
          darkmem
        </h1>
      </div>
      <p className="text-muted-foreground text-sm">{subtitle}</p>
    </div>
  )
}

/** A new-password field with the same show/hide trigger the login form has:
 *  on the one screen where a typo locks the only admin credential, the
 *  operator must be able to read back what they typed. */
export function SetupPasswordField(
  props: Omit<ComponentProps<typeof PasswordInputField>, "type">,
) {
  return (
    <PasswordInput>
      <PasswordInputControl>
        <PasswordInputField autoComplete="new-password" {...props} />
        <PasswordInputVisibilityTrigger>
          <PasswordInputIndicator
            visible={<EyeOff aria-hidden className="h-4 w-4" />}
            hidden={<Eye aria-hidden className="h-4 w-4" />}
          />
        </PasswordInputVisibilityTrigger>
      </PasswordInputControl>
    </PasswordInput>
  )
}
