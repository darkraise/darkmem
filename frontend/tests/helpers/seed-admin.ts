import { execFileSync } from "node:child_process"

const BACKEND_PYTHON =
  "/root/repositories/darkmem/backend/.venv/bin/python"

// Hardcoded to the shared dev stack's own Postgres — never a lane's
// numbered test/bench pair, and never overridable by env, per T1.58's
// Ruling 4. 127.0.0.1:5433 / darkmem / darkmem / darkmem matches
// docker-compose.dev.yml and the repo-root CLAUDE.md's documented
// dev-stack coordinates.
const SEED_SCRIPT = `
import asyncio
import os
import sys
import time

import asyncpg
import bcrypt


async def main() -> None:
    password = os.environ.get("E2E_ADMIN_PASSWORD")
    if not password:
        print("E2E_ADMIN_PASSWORD is not set.", file=sys.stderr)
        sys.exit(1)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = await asyncpg.connect(
        host="127.0.0.1", port=5433, user="darkmem", password="darkmem",
        database="darkmem",
    )
    try:
        # UPDATE-only, on purpose: this script seeds an EXISTING admin
        # account, it never runs initial setup. The row-count check (not
        # the SQL's absence of an INSERT) is what makes a never-initialized
        # stack fail loudly instead of silently doing nothing.
        status = await conn.execute(
            "UPDATE config SET value = jsonb_build_object('hash', $1::text) "
            "WHERE key = 'admin_password_hash'",
            hashed,
        )
        affected = int(status.rsplit(" ", 1)[-1])
        if affected == 0:
            print(
                "stack not initialized — run setup first, this script "
                "only seeds an existing admin account",
                file=sys.stderr,
            )
            sys.exit(1)

        # True upsert: admin_password_changed_at is written only by the
        # change-password route (routes/auth.py), so it legitimately does
        # not exist on a stack that was only ever initialized through
        # setup and never had its password changed via the UI. An
        # UPDATE-only second statement would silently no-op there and
        # leave the owner's pre-seed session token valid — exactly the
        # partial-corruption failure this upsert closes.
        await conn.execute(
            "INSERT INTO config (key, value) "
            "VALUES ('admin_password_changed_at', "
            "jsonb_build_object('ts', $1::bigint)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            int(time.time()),
        )
        print(f"seeded admin password (hash rows affected: {affected})")
    finally:
        await conn.close()


asyncio.run(main())
`

/**
 * Overwrite the shared dev stack's admin password with
 * E2E_ADMIN_PASSWORD, so auth.spec.ts can log in with a password it
 * actually knows. This is a direct write against the dev stack's real
 * `config` table (there is no HTTP path to set a *known* password once
 * /api/v1/setup/* has 403'd itself uninitialized) — authorised and
 * destructive on purpose (T1.58 Ruling 4). It never touches a lane's
 * numbered test/bench database.
 */
export function seedAdminPassword(): void {
  const password = process.env.E2E_ADMIN_PASSWORD
  if (!password) {
    throw new Error(
      "E2E_ADMIN_PASSWORD is not set — auth.spec.ts needs a known admin " +
        "password on the dev stack and refuses to guess or default one.",
    )
  }
  execFileSync(BACKEND_PYTHON, ["-c", SEED_SCRIPT], {
    env: { ...process.env, E2E_ADMIN_PASSWORD: password },
    stdio: "inherit",
  })
}
