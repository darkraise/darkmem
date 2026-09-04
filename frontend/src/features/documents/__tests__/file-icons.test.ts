import { describe, it, expect } from "vitest"
import { File, FileCode, FileText, Braces, Settings2 } from "lucide-react"

import { fileIcon } from "../file-icons"

describe("fileIcon", () => {
  it("picks an icon from the extension", () => {
    expect(fileIcon("progress.md").icon).toBe(FileText)
    expect(fileIcon("parse-ledger.ts").icon).toBe(FileCode)
    expect(fileIcon("package.json").icon).toBe(Braces)
    expect(fileIcon("docker-compose.yml").icon).toBe(Settings2)
  })

  it("matches the extension case-insensitively", () => {
    expect(fileIcon("README.MD").icon).toBe(FileText)
  })

  it("uses the last dot segment, not the first", () => {
    // `docker-compose.dev.yml` is a real name in this repo, and splitting on
    // the first dot reads its extension as `dev`.
    expect(fileIcon("docker-compose.dev.yml").icon).toBe(Settings2)
  })

  it("falls back rather than guessing", () => {
    // A wrong icon is worse than a plain one: it is read as information.
    expect(fileIcon("Makefile").icon).toBe(File)
    expect(fileIcon("archive.xyz").icon).toBe(File)
    expect(fileIcon(".gitignore").icon).toBe(File)
    expect(fileIcon("trailing.").icon).toBe(File)
  })
})
