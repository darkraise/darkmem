import { useForm } from "@tanstack/react-form"
import { FieldWrapper } from "darkraise-ui/forms"
import { Button } from "darkraise-ui/components/button"
import {
  PasswordInput,
  PasswordInputControl,
  PasswordInputField,
  PasswordInputVisibilityTrigger,
  PasswordInputIndicator,
} from "darkraise-ui/components/password-input"
import { loginSchema } from "../schemas"
import { useLogin } from "../hooks/useLogin"
import { DEMO } from "@/lib/demo-flag"

export function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const login = useLogin()
  const form = useForm({
    defaultValues: { password: "" },
    onSubmit: async ({ value }) => {
      // Demo submit is a no-op: any password signs into the demo store.
      if (DEMO) {
        onSuccess()
        return
      }
      await login.mutateAsync(value)
      onSuccess()
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
      className="space-y-4"
    >
      <form.Field
        name="password"
        validators={{
          onChange: ({ value }) => {
            const result = loginSchema.shape.password.safeParse(value)
            return result.success ? undefined : result.error.issues[0]?.message
          },
        }}
      >
        {(field) => (
          <FieldWrapper
            name={field.name}
            label="Password"
            isInvalid={field.state.meta.errors.length > 0}
            errors={
              field.state.meta.errors.length > 0
                ? field.state.meta.errors.map((e) => ({
                    message: e ?? undefined,
                  }))
                : undefined
            }
          >
            {(isInvalid, ariaDescribedBy) => (
              <PasswordInput>
                <PasswordInputControl className="h-[42px] rounded-[10px] border border-white/15 bg-black/35 focus-within:ring-2 focus-within:ring-cyan-300/60">
                  <PasswordInputField
                    id={field.name}
                    autoComplete="current-password"
                    autoFocus
                    className="bg-transparent text-slate-100 placeholder:text-slate-400 focus:shadow-none focus-visible:shadow-none"
                    value={field.state.value}
                    aria-invalid={isInvalid}
                    aria-describedby={ariaDescribedBy}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                  />
                  <PasswordInputVisibilityTrigger>
                    <PasswordInputIndicator />
                  </PasswordInputVisibilityTrigger>
                </PasswordInputControl>
              </PasswordInput>
            )}
          </FieldWrapper>
        )}
      </form.Field>

      <Button
        type="submit"
        disabled={login.isPending}
        className="dm-btn-pulse w-full bg-gradient-to-r from-[#818cf8] via-[#6366f1] to-[#38bdf8] font-semibold text-slate-950 focus-visible:ring-2 focus-visible:ring-cyan-300/70 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:bg-slate-700 disabled:bg-none disabled:text-slate-100 disabled:opacity-100"
      >
        {login.isPending ? "Signing in…" : "Sign in"}
      </Button>

      {login.isError && (
        <p
          role="alert"
          className="bg-destructive/15 text-destructive rounded-md px-3 py-2 text-sm"
        >
          {(login.error as Error).message}
        </p>
      )}
    </form>
  )
}
