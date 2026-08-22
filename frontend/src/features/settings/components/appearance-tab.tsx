import { Palette } from "lucide-react"
import { ThemeSettingsPanel } from "darkraise-ui/theme"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { HelpTip } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"

/**
 * Every theme axis the library exposes, in the library's own page layout.
 *
 * The header popover deliberately shows three of them (`SWITCHER_AXES`); this
 * is where the rest live. Both surfaces drive the one `ThemeProvider`, so a
 * change here is the same change the popover would make — there is no draft to
 * apply and no Save button to look for.
 */
export function AppearanceTab() {
  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 overflow-hidden border-b px-4 py-2.5">
        <Palette aria-hidden className="text-primary h-4 w-4 shrink-0" />
        <h3 className="text-foreground min-w-0 truncate font-mono text-[11px] font-semibold tracking-[0.14em] uppercase">
          Theme axes
        </h3>
        <span className="shrink-0">
          <HelpTip label="About Theme axes">
            {DEMO
              ? "Demo mode has no backend, so a choice here persists in this browser only."
              : "A choice applies immediately and is saved server-side, so it follows you to another browser."}
          </HelpTip>
        </span>
        <span className="flex-1" />
        <span className="text-muted-foreground shrink-0 text-xs">
          Header palette button: mode and the two colours
        </span>
      </CardHeader>
      <CardContent className="p-4">
        <ThemeSettingsPanel layout="page" />
      </CardContent>
    </Card>
  )
}
