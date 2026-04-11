// darkraise-ui 1.0.5 ships a CommandDialog that wraps Radix Dialog.Content
// without rendering DialogTitle/DialogDescription. Radix logs two errors on
// every Cmd-K open. There is no consumer-side prop to supply the title, so
// until darkraise-ui ships a version that accepts it, filter the two specific
// warnings. Remove when darkraise-ui exposes title/description on CommandDialog.
const UPSTREAM_WARNING_FRAGMENTS = [
  "`DialogContent` requires a `DialogTitle`",
  "Missing `Description` or `aria-describedby",
]

export function suppressUpstreamDarkraiseWarnings(): void {
  const originalError = console.error
  console.error = (...args: unknown[]) => {
    const first = args[0]
    if (
      typeof first === "string" &&
      UPSTREAM_WARNING_FRAGMENTS.some((fragment) => first.includes(fragment))
    ) {
      return
    }
    originalError.apply(console, args)
  }
}
