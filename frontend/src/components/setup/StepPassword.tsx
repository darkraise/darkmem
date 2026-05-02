import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { useSetupWizardStore } from "@/features/setup/setupWizardStore"

export function StepPassword() {
  const password = useSetupWizardStore((s) => s.password)
  const setPassword = useSetupWizardStore((s) => s.setPassword)

  const error =
    password.value.length > 0 && password.value.length < 8
      ? "Password must be at least 8 characters"
      : password.confirm.length > 0 && password.value !== password.confirm
        ? "Passwords do not match"
        : null

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label htmlFor="password">Admin password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          value={password.value}
          onChange={(e) => setPassword(e.target.value, password.confirm)}
          placeholder="At least 8 characters"
          autoFocus
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="confirm">Confirm password</Label>
        <Input
          id="confirm"
          type="password"
          autoComplete="new-password"
          value={password.confirm}
          onChange={(e) => setPassword(password.value, e.target.value)}
          placeholder="Repeat password"
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

export function isStepPasswordValid(state: { value: string; confirm: string }): boolean {
  return state.value.length >= 8 && state.value === state.confirm
}
