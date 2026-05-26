import { Button } from "darkraise-ui/components/button"
import type { ComponentProps } from "react"

export const CHAT_GRADIENT_CLASS =
  "bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400"

export function ChatGradientButton({
  className = "",
  ...props
}: ComponentProps<typeof Button>) {
  return (
    <Button
      className={`border-0 ${CHAT_GRADIENT_CLASS} ${className}`}
      {...props}
    />
  )
}
