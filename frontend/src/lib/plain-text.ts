/**
 * Markdown emphasis, removed for a field rendered as plain text.
 *
 * The ledger's Note and Review cells and the epic files' gate prose are
 * markdown, and the board renders them as text -- so an entry gate reached the
 * dialog reading literally `**G-Z** holds T9.02 only.` A document block's text
 * is the same case wherever it is quoted as a preview (search hits,
 * connections, related memories).
 *
 * Deliberately not a markdown renderer. These fields are one paragraph of
 * prose in a card or a dialog row; parsing them properly would pull a renderer
 * into a surface that wants no links, no headings and no lists. This strips
 * the three inline markers that actually occur and leaves everything else
 * alone -- including a lone `*`, which is a bullet or a footnote far more
 * often than an unclosed emphasis.
 */
export function plainText(markdown: string): string {
  return markdown
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/(^|[\s(])_(?!_)(.+?)_(?=[\s.,;:)!?]|$)/g, "$1$2")
    .replace(/`([^`]+)`/g, "$1")
    .trim()
}
