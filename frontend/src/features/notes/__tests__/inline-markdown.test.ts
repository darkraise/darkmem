import { describe, expect, it } from "vitest"
import { emitInline, parseInline, type InlineNode, type InlineStyles } from "../lib/inline-markdown"
import { pick, rng } from "./seeded"

const ALPHABET = ["a", "b", "Z", "1", " ", "  ", "\n", "*", "_", "`", "~", "[", "]", "(", ")", "<", ">", "&", "#", "\\", "!", "|", "-", "+", ".", "é", "&amp;", "http://x.y", "1.", "# "]

function genText(r: () => number): string {
  let out = ""
  const n = 1 + Math.floor(r() * 5)
  for (let i = 0; i < n; i++) out += pick(ALPHABET, r)
  return out
}

function genStyles(r: () => number): InlineStyles {
  const s: InlineStyles = {}
  if (r() < 0.3) s.bold = true
  if (r() < 0.3) s.italic = true
  if (r() < 0.2) s.strike = true
  if (r() < 0.15) s.code = true
  return s
}

function genContent(r: () => number): InlineNode[] {
  const out: InlineNode[] = []
  const n = Math.floor(r() * 5)
  for (let i = 0; i < n; i++) {
    const k = r()
    if (k < 0.75) out.push({ type: "text", text: genText(r), styles: genStyles(r) })
    else if (k < 0.9) out.push({ type: "link", href: "https://ex.am/p?q=" + Math.floor(r() * 9), content: [{ type: "text", text: genText(r).replace(/\n/g, "") || "l", styles: genStyles(r) }] })
    else out.push({ type: "rawInline", props: { source: pick(["<kbd>", "![i](u)", "<http://a.b>", '[t](u "t")'], r) } })
  }
  return out
}

const WORDS = ["alpha", "Beta", "x1", "déjà", "a_b", "2*3", "c++", "don't", "e.g.", "50%", "[x]", "<tag>", "&amp;", "~tilde~", "`tick`", "#hash", "1."]

/** Content the way typing produces it: a styled run starts and ends on a
 *  word, and runs are separated by plain spaces or punctuation. */
function genTyped(r: () => number): InlineNode[] {
  const out: InlineNode[] = []
  const n = 1 + Math.floor(r() * 4)
  for (let i = 0; i < n; i++) {
    if (i > 0) out.push({ type: "text", text: pick([" ", ", ", " - ", "\n"], r), styles: {} })
    const words = Array.from({ length: 1 + Math.floor(r() * 3) }, () => pick(WORDS, r)).join(" ")
    if (r() < 0.2) out.push({ type: "link", href: "https://ex.am/" + i, content: [{ type: "text", text: words.replace(/`/g, ""), styles: {} }] })
    else out.push({ type: "text", text: words, styles: genStyles(r) })
  }
  return out
}

type Cell = [string, boolean, boolean, boolean, boolean, string | null]

function cells(nodes: InlineNode[]): Cell[] {
  const out: Cell[] = []
  for (const n of nodes) {
    if (n.type === "rawInline") out.push([n.props.source, false, false, false, false, "atom"])
    const runs = n.type === "text" ? [n] : n.type === "link" ? n.content : []
    const href = n.type === "link" ? n.href : null
    for (const run of runs)
      for (const ch of run.text) {
        const styled = ch.trim() !== ""
        out.push([ch, styled && !!run.styles.bold, styled && !!run.styles.italic, styled && !!run.styles.strike, ch !== "\n" && !!run.styles.code, href])
      }
  }
  return out
}

describe("inline markdown", () => {
  it("settles: emit(parse(emit(c))) === emit(c) for arbitrary content", () => {
    const r = rng(7)
    for (let i = 0; i < 5000; i++) {
      const c = genContent(r)
      const once = emitInline(c)
      const twice = emitInline(parseInline(once))
      if (twice !== once) throw new Error(`case ${i}: ${JSON.stringify(c)}\nonce=${JSON.stringify(once)}\ntwice=${JSON.stringify(twice)}`)
    }
  })

  it("keeps every character, mark and link of typed content", () => {
    const r = rng(11)
    for (let i = 0; i < 5000; i++) {
      const c = genTyped(r)
      const back = parseInline(emitInline(c))
      if (JSON.stringify(cells(back)) !== JSON.stringify(cells(c)))
        throw new Error(`case ${i}: ${JSON.stringify(c)} -> ${JSON.stringify(emitInline(c))} -> ${JSON.stringify(back)}`)
    }
  })

  it("keeps every visible character of arbitrary content", () => {
    const r = rng(13)
    for (let i = 0; i < 5000; i++) {
      const c = genContent(r)
      const text = (nodes: InlineNode[]) => cells(nodes).map((x) => x[0]).join("").replace(/\s+/g, "")
      const back = parseInline(emitInline(c))
      if (text(back) !== text(c)) throw new Error(`case ${i}: ${JSON.stringify(c)} -> ${JSON.stringify(emitInline(c))}`)
    }
  })

  it.each([
    ["<kbd>k</kbd> tail", "<kbd>"],
    ["an ![img](u) here", "![img](u)"],
    ["go <http://a.b> now", "<http://a.b>"],
    ['[t](u "title")', '[t](u "title")'],
    ["**bold ![i](u)**", "**bold ![i](u)**"],
    ["hard  \nbreak", "  \n"],
  ])("keeps %j byte for byte through an edit elsewhere", (text, atom) => {
    const nodes = parseInline(text)
    expect(nodes.some((n) => n.type === "rawInline" && n.props.source === atom)).toBe(true)
    const edited: InlineNode[] = [...nodes, { type: "text", text: " more", styles: {} }]
    expect(emitInline(edited)).toContain(atom)
  })

  it("reads a reference link or footnote with no definition as text", () => {
    expect(parseInline("see [x][1]")).toEqual([{ type: "text", text: "see [x][1]", styles: {} }])
    expect(parseInline(emitInline(parseInline("note[^n]")))).toEqual([{ type: "text", text: "note[^n]", styles: {} }])
  })
  it("maps marks and inline links", () => {
    expect(parseInline("a **b** *c* `d` ~~e~~ [f](https://x.y)")).toEqual([
      { type: "text", text: "a ", styles: {} },
      { type: "text", text: "b", styles: { bold: true } },
      { type: "text", text: " ", styles: {} },
      { type: "text", text: "c", styles: { italic: true } },
      { type: "text", text: " ", styles: {} },
      { type: "text", text: "d", styles: { code: true } },
      { type: "text", text: " ", styles: {} },
      { type: "text", text: "e", styles: { strike: true } },
      { type: "text", text: " ", styles: {} },
      { type: "link", href: "https://x.y", content: [{ type: "text", text: "f", styles: {} }] },
    ])
  })

  it("does not read block markers in inline text", () => {
    expect(parseInline("# not a heading")).toEqual([{ type: "text", text: "# not a heading", styles: {} }])
    expect(parseInline("- not a list")).toEqual([{ type: "text", text: "- not a list", styles: {} }])
  })

  it("decodes escapes and entities, then escapes them back", () => {
    expect(parseInline("\\*lit\\* &lt;kbd&gt;")).toEqual([{ type: "text", text: "*lit* <kbd>", styles: {} }])
    const back = emitInline(parseInline("\\*lit\\* &lt;kbd&gt;"))
    expect(parseInline(back)).toEqual([{ type: "text", text: "*lit* <kbd>", styles: {} }])
  })

  it("keeps a soft line break as a newline", () => {
    expect(parseInline("one\ntwo")).toEqual([{ type: "text", text: "one\ntwo", styles: {} }])
    expect(emitInline(parseInline("one\ntwo"))).toBe("one\ntwo")
  })

  it("keeps text it cannot rebuild as one atom", () => {
    expect(parseInline("a\n\nb")).toEqual([{ type: "rawInline", props: { source: "a\n\nb" } }])
  })

  it("empty text is no content", () => {
    expect(parseInline("")).toEqual([])
    expect(emitInline([])).toBe("")
  })
})
