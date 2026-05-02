"""Phase 1: authentication flow.

Covers setup, login, /me, refresh, change-password, logout, revocation,
and WebSocket auth.
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

from lib.client import DarkmemClient, TestReport, parse_args
from lib.assertions import assert_status


async def _auto_recover_password(base: str, expected: str, temp: str) -> None:
    """If a prior run left the password as `temp`, restore it to `expected`.

    The change-password test wraps its mutations in try/finally but if the
    script is killed mid-run (or the revert itself fails), the server can be
    left with `temp` as the current password. On the next run we detect that
    and restore before the main flow starts.
    """
    async with httpx.AsyncClient(timeout=10.0) as c:
        # Try expected first
        r = await c.post(f"{base}/api/v1/auth/login", json={"password": expected})
        if r.status_code == 200:
            return
        # Try temp as current
        r = await c.post(f"{base}/api/v1/auth/login", json={"password": temp})
        if r.status_code != 200:
            return  # can't recover; let main flow report the actual state
        cookie = r.cookies.get("darkmem_session")
        if not cookie:
            return
        await c.post(
            f"{base}/api/v1/auth/change-password",
            json={"current_password": temp, "new_password": expected},
            cookies={"darkmem_session": cookie},
        )
        print("  [RECOVER] restored password from temp to expected")


async def main() -> int:
    args = parse_args("Phase 1: auth flow")
    report = TestReport("Phase 1 - Auth flow")

    # If a prior run left the password in an inconsistent state, fix it first.
    await _auto_recover_password(args.base_url, args.password, args.password + "-temp")

    async with httpx.AsyncClient(timeout=30.0) as raw:
        base = args.base_url

        # 1.1 setup
        status = (await raw.get(f"{base}/api/v1/setup/status")).json()
        is_initialized = status.get("initialized", False)

        if not is_initialized:
            # Try short password (should 422)
            r = await raw.post(f"{base}/api/v1/setup", json={"password": "short"})
            if r.status_code == 422:
                report.ok("setup rejects password < 8 chars")
            else:
                report.fail("setup short password", f"status {r.status_code}")

            # Try too-long password (should 422)
            r = await raw.post(f"{base}/api/v1/setup", json={"password": "x" * 200})
            if r.status_code == 422:
                report.ok("setup rejects password > 128 chars")
            else:
                report.fail("setup long password", f"status {r.status_code}")

            # Valid setup
            r = await raw.post(f"{base}/api/v1/setup", json={"password": args.password})
            if assert_status(r, 200, "setup with valid password"):
                report.ok("setup with valid password")
                cookie_header = r.headers.get("set-cookie", "")
                header_lower = cookie_header.lower()
                if "httponly" in header_lower and "samesite=strict" in header_lower:
                    report.ok("session cookie has HttpOnly and SameSite=strict")
                else:
                    report.fail("cookie attributes", cookie_header)
        else:
            report.warn("already initialized — skipping setup tests")

        # Setup again should 403 (already initialized)
        r = await raw.post(f"{base}/api/v1/setup", json={"password": args.password})
        if r.status_code == 403:
            report.ok("second setup returns 403")
        else:
            report.fail("second setup", f"status {r.status_code}")

        # 1.2 login — wrong password
        r = await raw.post(f"{base}/api/v1/auth/login", json={"password": "wrong-password"})
        if r.status_code == 401:
            report.ok("login with wrong password returns 401")
        else:
            report.fail("login wrong password", f"status {r.status_code}")

        # Login — correct
        r = await raw.post(f"{base}/api/v1/auth/login", json={"password": args.password})
        if assert_status(r, 200, "login correct password"):
            report.ok("login with correct password")
            cookie = r.cookies.get("darkmem_session")
        else:
            return report.summary()

        # /me with cookie
        r = await raw.get(f"{base}/api/v1/auth/me", cookies={"darkmem_session": cookie})
        if r.status_code == 200 and r.json().get("authenticated"):
            report.ok("/auth/me authenticated")
        else:
            report.fail("/auth/me with cookie", f"status {r.status_code}")

        # /me without cookie — use a SEPARATE client so the shared cookie jar doesn't leak
        async with httpx.AsyncClient(timeout=30.0) as clean:
            r = await clean.get(f"{base}/api/v1/auth/me")
            if r.status_code == 401:
                report.ok("/auth/me without cookie returns 401")
            else:
                report.fail("/auth/me without cookie", f"status {r.status_code}")

            # /me with bad bearer (clean client, no cookie)
            r = await clean.get(
                f"{base}/api/v1/auth/me",
                headers={"Authorization": "Bearer not-a-real-token"},
            )
            if r.status_code == 401:
                report.ok("/auth/me with malformed bearer returns 401")
            else:
                report.fail("/auth/me bad bearer", f"status {r.status_code}")

        # 1.3 refresh
        r = await raw.post(f"{base}/api/v1/auth/refresh", cookies={"darkmem_session": cookie})
        if r.status_code == 200 and r.cookies.get("darkmem_session"):
            report.ok("refresh returns new session cookie")
            cookie = r.cookies.get("darkmem_session") or cookie
        else:
            report.fail("refresh", f"status {r.status_code}")

        # change-password wrong current
        r = await raw.post(
            f"{base}/api/v1/auth/change-password",
            json={"current_password": "bogus", "new_password": "new-e2e-pw-123"},
            cookies={"darkmem_session": cookie},
        )
        if r.status_code == 401:
            report.ok("change-password rejects wrong current")
        else:
            report.fail("change-password wrong current", f"status {r.status_code}")

        # change-password short new
        r = await raw.post(
            f"{base}/api/v1/auth/change-password",
            json={"current_password": args.password, "new_password": "short"},
            cookies={"darkmem_session": cookie},
        )
        if r.status_code == 422:
            report.ok("change-password rejects short new password")
        else:
            report.fail("change-password short new", f"status {r.status_code}")

        # Valid change (use a temp password then revert)
        # Wrapped in try/finally so a failure halfway doesn't leave the
        # server in an inconsistent password state that breaks the next run.
        temp_password = args.password + "-temp"
        password_changed_to_temp = False
        try:
            r = await raw.post(
                f"{base}/api/v1/auth/change-password",
                json={"current_password": args.password, "new_password": temp_password},
                cookies={"darkmem_session": cookie},
            )
            if r.status_code == 200:
                report.ok("change-password with valid payload")
                password_changed_to_temp = True
            else:
                report.fail("change-password valid", f"status {r.status_code}")

            # Login with new password (clean client to avoid cookie jar carryover)
            async with httpx.AsyncClient(timeout=30.0) as clean:
                r = await clean.post(f"{base}/api/v1/auth/login", json={"password": temp_password})
                if r.status_code == 200:
                    report.ok("login with new password")
                else:
                    report.fail("login new password", f"status {r.status_code}: {r.text[:100]}")
        finally:
            if password_changed_to_temp:
                # Always try to revert, even if the login test above failed.
                # Use a clean client so we can re-login on the temp password explicitly.
                async with httpx.AsyncClient(timeout=30.0) as revert_client:
                    lr = await revert_client.post(
                        f"{base}/api/v1/auth/login",
                        json={"password": temp_password},
                    )
                    revert_cookie = lr.cookies.get("darkmem_session")
                    if revert_cookie:
                        rv = await revert_client.post(
                            f"{base}/api/v1/auth/change-password",
                            json={"current_password": temp_password, "new_password": args.password},
                            cookies={"darkmem_session": revert_cookie},
                        )
                        if rv.status_code == 200:
                            report.ok("revert password")
                        else:
                            report.fail("revert password", f"status {rv.status_code}")
                    else:
                        report.fail("revert password", "could not re-login on temp password")

        # Re-login with original (clean client)
        async with httpx.AsyncClient(timeout=30.0) as clean:
            r = await clean.post(f"{base}/api/v1/auth/login", json={"password": args.password})
            if r.status_code == 200:
                cookie = r.cookies.get("darkmem_session") or cookie

        # 1.4 logout and revocation
        r = await raw.post(f"{base}/api/v1/auth/logout", cookies={"darkmem_session": cookie})
        if r.status_code == 200:
            report.ok("logout returns 200")
        else:
            report.fail("logout", f"status {r.status_code}")

        # Authed call with old cookie should fail
        r = await raw.get(f"{base}/api/v1/auth/me", cookies={"darkmem_session": cookie})
        if r.status_code == 401:
            report.ok("authed call with revoked cookie returns 401")
        else:
            report.fail("revoked cookie", f"status {r.status_code}")

        # Re-login for downstream tests
        r = await raw.post(f"{base}/api/v1/auth/login", json={"password": args.password})
        if r.status_code == 200:
            report.ok("final re-login ok")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
