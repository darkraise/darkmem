import { Label } from "darkraise-ui/components/label"
import { useSetupWizardStore } from "@/features/setup/setupWizardStore"
import { SetupPasswordField } from "./setup-brand"
import {
  PASSWORD_MAX_BYTES,
  PASSWORD_MIN_CHARS,
  passwordTooLong,
} from "@/lib/password-rules"

export function StepPassword() {
  const password = useSetupWizardStore((s) => s.password)
  const setPassword = useSetupWizardStore((s) => s.setPassword)

  const error =
    password.value.length > 0 && password.value.length < PASSWORD_MIN_CHARS
      ? `Password must be at least ${PASSWORD_MIN_CHARS} characters`
      : passwordTooLong(password.value)
        ? `Password must be at most ${PASSWORD_MAX_BYTES} bytes (accented and non-Latin characters count as more than one)`
        : password.confirm.length > 0 && password.value !== password.confirm
          ? "Passwords do not match"
          : null

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label htmlFor="password">Admin password</Label>
        <SetupPasswordField
          id="password"
          value={password.value}
          onChange={(e) => setPassword(e.target.value, password.confirm)}
          placeholder="At least 8 characters"
          autoFocus
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="confirm">Confirm password</Label>
        <SetupPasswordField
          id="confirm"
          value={password.confirm}
          onChange={(e) => setPassword(password.value, e.target.value)}
          placeholder="Repeat password"
        />
      </div>
      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}
    </div>
  )
}

export function isStepPasswordValid(state: {
  value: string
  confirm: string
}): boolean {
  return (
    state.value.length >= PASSWORD_MIN_CHARS &&
    !passwordTooLong(state.value) &&
    state.value === state.confirm
  )
}
