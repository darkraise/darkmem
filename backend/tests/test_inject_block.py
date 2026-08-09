"""T3.09 — the marker-bounded managed block (doc 15 §3.1–§3.2).

The whole trust posture of inject is one sentence: **the server never writes
the client's filesystem**, and within the file the client does write, darkmem
owns only the bytes between two markers. So this suite spends almost all of
itself on the ways that boundary can be violated, and very little on the happy
path.

Three properties, in the order they matter:

1. **Human content is inviolable.** Everything outside the markers survives a
   rewrite byte for byte — not "logically equivalent", byte for byte, because
   a writer that normalised a user's line endings or trailing whitespace has
   still edited their file.
2. **A damaged marker pair fails safe.** Missing, unpaired, inverted or
   duplicated markers all refuse to write. The failure mode this forbids is
   *guessing* — a writer that picked the first plausible region would silently
   eat whatever a stray marker happened to bracket.
3. **No server-side filesystem write exists in the path**, asserted by a scan
   over the module rather than by reading it once and trusting the next
   author.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.services import inject_block as ib
from app.services.inject_block import (
    ManagedBlockCorrupted,
    apply_block,
    remove_block,
    render_block,
)

HUMAN_ABOVE = "# My rules\n\nAlways run the linter.\n\n"
HUMAN_BELOW = "\n## Notes\n\nDo not delete this.\n"


def _wrap(inner: str) -> str:
    return f"{HUMAN_ABOVE}{ib.MARKER_BEGIN}\n{inner}\n{ib.MARKER_END}{HUMAN_BELOW}"


# ─────────────── property 1: human content is inviolable ───────────────


class TestHumanContentSurvives:
    def test_text_outside_the_markers_is_preserved_byte_for_byte(self):
        original = _wrap("old block")

        updated = apply_block(original, "new block")

        assert updated.startswith(HUMAN_ABOVE)
        assert updated.endswith(HUMAN_BELOW)
        assert "old block" not in updated
        assert "new block" in updated

    def test_odd_whitespace_and_line_endings_outside_are_untouched(self):
        """A writer that normalised these has edited the human's file. CRLF is
        the case that matters in practice: a Windows user's context file
        rewritten to LF is a diff they did not ask for."""
        above = "# Rules\r\n\r\n  indented\t\r\n"
        below = "\r\n\r\ntrailing spaces here   \r\n\r\n"
        original = f"{above}{ib.MARKER_BEGIN}\nold\n{ib.MARKER_END}{below}"

        updated = apply_block(original, "new")

        assert updated.startswith(above)
        assert updated.endswith(below)

    def test_a_file_with_no_block_gets_one_appended_and_keeps_its_content(self):
        original = "# Just my rules\n\nnothing else here\n"

        updated = apply_block(original, "injected")

        assert updated.startswith(original)
        assert ib.MARKER_BEGIN in updated and ib.MARKER_END in updated
        assert "injected" in updated

    def test_an_empty_file_is_a_first_write_not_an_error(self):
        updated = apply_block("", "injected")
        assert ib.MARKER_BEGIN in updated
        assert "injected" in updated

    def test_markers_inside_the_human_s_own_prose_are_still_the_block(self):
        """Stated so the limit is known rather than discovered: the markers are
        a fixed sentinel, so a human who pastes one into their own notes has
        declared a block there. This is why the sentinel is long and
        distinctive, and why a *damaged* pair refuses rather than guesses."""
        original = f"{ib.MARKER_BEGIN}\nx\n{ib.MARKER_END}\n"
        assert "y" in apply_block(original, "y")


# ─────────────── property 2: idempotence ───────────────


class TestIdempotence:
    def test_re_injecting_the_same_content_is_a_fixed_point(self):
        """Strip-before-rewrite, the invariant-8 analogue: repeated refresh
        under any cadence must not accumulate blocks."""
        once = apply_block(_wrap("old"), "same")
        twice = apply_block(once, "same")

        assert once == twice

    def test_repeated_refresh_never_accumulates_a_second_block(self):
        text = "# rules\n"
        for index in range(5):
            text = apply_block(text, f"round {index}")

        assert text.count(ib.MARKER_BEGIN) == 1
        assert text.count(ib.MARKER_END) == 1
        assert "round 4" in text and "round 3" not in text


# ─────────────── property 3: a damaged pair fails safe ───────────────


class TestADamagedPairRefusesToWrite:
    """Every case here must raise. The forbidden behaviour is *guessing* —
    picking the first plausible region and writing into it, which is how a
    writer eats the bytes a stray marker happened to bracket.
    """

    @pytest.mark.parametrize(
        "broken,why",
        [
            (f"# rules\n{ib.MARKER_BEGIN}\nno end marker\n", "begin without end"),
            (f"# rules\nno begin marker\n{ib.MARKER_END}\n", "end without begin"),
            (
                f"{ib.MARKER_END}\ninverted\n{ib.MARKER_BEGIN}\n",
                "end before begin",
            ),
            (
                f"{ib.MARKER_BEGIN}\na\n{ib.MARKER_BEGIN}\nb\n{ib.MARKER_END}\n",
                "two begins",
            ),
            (
                f"{ib.MARKER_BEGIN}\na\n{ib.MARKER_END}\nb\n{ib.MARKER_END}\n",
                "two ends",
            ),
        ],
    )
    def test_a_corrupted_pair_raises_and_returns_nothing(self, broken, why):
        # `why` labels the case in the test id; the assertion is the raise
        # itself. An earlier draft also matched on the message and did it with
        # an `or` that made the whole expression truthy -- a check that could
        # not fail, in the suite whose subject is writers that guess.
        with pytest.raises(ManagedBlockCorrupted):
            apply_block(broken, "new")

    def test_the_refusal_names_the_file_shape_it_found(self):
        """The operator has to fix this by hand in their own file, so the
        error must say what was wrong — a bare 'corrupted' sends them looking
        at darkmem instead of at their markers."""
        with pytest.raises(ManagedBlockCorrupted) as refusal:
            apply_block(f"{ib.MARKER_BEGIN}\nunterminated\n", "new")

        message = str(refusal.value)
        assert ib.MARKER_END in message
        assert "1" in message  # the counts it actually saw

    def test_removal_of_a_corrupted_pair_also_refuses(self):
        """Remove is a write too. A damaged pair is exactly when 'just clean
        it up' is most tempting and most destructive."""
        with pytest.raises(ManagedBlockCorrupted):
            remove_block(f"{ib.MARKER_BEGIN}\nunterminated\n")


# ─────────────── the lifecycle doc 15 §3.2 draws ───────────────


class TestLifecycle:
    def test_curbing_leaves_an_empty_marker_pair_not_a_hole(self):
        """The `Curbed` state: the block is cleared, the markers stay, so the
        next refresh has somewhere to write and the human can see the feature
        is installed but silent."""
        curbed = apply_block(_wrap("content"), "")

        assert ib.MARKER_BEGIN in curbed and ib.MARKER_END in curbed
        assert "content" not in curbed
        assert apply_block(curbed, "back") .count(ib.MARKER_BEGIN) == 1

    def test_removal_takes_the_markers_with_it(self):
        """`Removed`: uninstall must not leave a sentinel pair behind, or the
        next install would treat the leftovers as its own block."""
        removed = remove_block(_wrap("content"))

        assert ib.MARKER_BEGIN not in removed
        assert ib.MARKER_END not in removed
        assert removed == HUMAN_ABOVE + HUMAN_BELOW

    def test_removing_from_a_file_with_no_block_changes_nothing(self):
        original = "# just rules\n"
        assert remove_block(original) == original


# ─────────────── the header the block carries ───────────────


class TestTheRenderedBlock:
    def test_the_header_states_provenance_and_scope(self):
        block = render_block(
            ["fact one", "fact two"], project="darkmem", generated_at="2026-08-09T10:00:00Z",
            token_budget=500,
        )

        assert "darkmem" in block
        assert "2026-08-09T10:00:00Z" in block
        assert "2 items" in block
        assert "500" in block

    def test_the_rendered_block_round_trips_through_apply(self):
        block = render_block(
            ["only item"], project="p", generated_at="2026-08-09T10:00:00Z",
            token_budget=100,
        )
        written = apply_block("# rules\n", block)

        assert "only item" in written
        assert apply_block(written, block) == written

    def test_a_marker_in_the_project_name_is_refused_too(self):
        """The header interpolates `project` and `generated_at`, both free-form,
        so checking only the items left the header as a way in. Found by the
        2026-08-09 task review (I-1): a project so named wrote a two-END file,
        and the next refresh *and* uninstall then both refused — locking the
        human out of their own file on damage darkmem itself caused.
        """
        with pytest.raises(ManagedBlockCorrupted):
            render_block(
                ["fine"], project=f"proj {ib.MARKER_END}",
                generated_at="2026-08-09T10:00:00Z", token_budget=100,
            )

    def test_apply_refuses_a_block_carrying_a_marker_whoever_rendered_it(self):
        """The check belongs at the write boundary, not only at rendering: a
        per-tool adapter (T3.11) may compose its own block, and `apply_block`
        is where the bytes actually land.
        """
        with pytest.raises(ManagedBlockCorrupted):
            apply_block("# rules\n", f"body {ib.MARKER_BEGIN} more")

    def test_the_refusal_leaves_the_file_untouched(self):
        """A refusal that had already written is not a refusal."""
        original = _wrap("old")
        with pytest.raises(ManagedBlockCorrupted):
            apply_block(original, f"bad {ib.MARKER_END}")
        assert "old" in original and original.count(ib.MARKER_END) == 1

    def test_an_item_containing_a_marker_is_refused_not_embedded(self):
        """The one way rendering could corrupt the file it is written into:
        an item carrying a sentinel would create a second pair, and the next
        refresh would refuse on a file darkmem itself broke."""
        with pytest.raises(ManagedBlockCorrupted):
            render_block(
                [f"innocent {ib.MARKER_END} text"], project="p",
                generated_at="2026-08-09T10:00:00Z", token_budget=100,
            )


# ─────────────── property 3: no server-side filesystem write ───────────────


def test_the_module_performs_no_filesystem_write_at_all():
    """Done-when 3, asserted structurally rather than by reading it once.

    The trust posture is that the *client* writes its own file; a server-side
    write in this path would invert it. This scans for the shapes that could:
    `open`, `Path.write_*`, `os.*` writers, `shutil`, and any import of a
    filesystem module. A function that merely returns text cannot write a
    file, so the absence of these is the property.
    """
    source = Path(inspect.getfile(ib)).read_text()
    tree = ast.parse(source)

    # An allowlist, not only a denylist. The 2026-08-09 task review measured
    # this scan's reach: `import os` + `os.replace` reddens it, but
    # `__import__("os").replace(...)` slips the call check (the `str.replace`
    # carve-out exempts exactly that name), and a write hidden behind any
    # `app.*` helper passes entirely. This module needs two imports and will
    # never need a third, so pinning the set closes the realistic drift shape
    # — a later author reaching for a filesystem helper trips here first.
    allowed_imports = {"__future__", "dataclasses"}

    forbidden_calls = {
        "open", "write_text", "write_bytes", "writelines", "remove", "unlink",
        "rename", "replace", "mkdir", "makedirs", "rmtree", "copy", "copyfile",
    }
    forbidden_modules = {"os", "io", "shutil", "pathlib", "tempfile", "aiofiles"}

    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            # `str.replace` is not a filesystem call; only the module-level
            # `os.replace` is, and that is caught by the import ban below.
            if name in forbidden_calls and name != "replace":
                offenders.append(f"{node.lineno}: calls {name}()")
            if name == "__import__":
                offenders.append(f"{node.lineno}: calls __import__()")
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_modules or root not in allowed_imports:
                    offenders.append(f"{node.lineno}: imports {alias.name}")
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in forbidden_modules or root not in allowed_imports:
                offenders.append(f"{node.lineno}: imports from {node.module}")

    assert not offenders, (
        "the managed-block writer must not touch a filesystem — the client "
        "writes its own file and the server never does:\n  "
        + "\n  ".join(offenders)
    )


def test_the_public_surface_is_text_in_text_out():
    """The same property from the other side: every public function takes and
    returns `str`, so there is no path shape for a caller to hand in."""
    for name in ("apply_block", "remove_block", "render_block"):
        signature = inspect.signature(getattr(ib, name))
        assert signature.return_annotation == "str", name
        for param in signature.parameters.values():
            assert "Path" not in str(param.annotation), f"{name}.{param.name}"
