from app.services.notion_content import resolve_target, scan_links


def _targets(source: str) -> list[str]:
    return [span.destination for span in scan_links(source)]


def test_a_plain_link_is_found():
    assert _targets("see [docs](a.md) here") == ["a.md"]


def test_balanced_parentheses_in_a_target_are_kept():
    # The real export holds nine of these, e.g. "1 Image (no compress) + ...".
    source = "[shot](1%20Image%20(no%20compress)%20plan%20abc.md)"
    assert _targets(source) == ["1%20Image%20(no%20compress)%20plan%20abc.md"]


def test_nested_balanced_parentheses_are_kept():
    assert _targets("[x](a((b))c.md)") == ["a((b))c.md"]


def test_an_unbalanced_parenthesis_stops_at_the_first_close():
    assert _targets("[x](a(b.md) tail") == []


def test_the_angle_bracket_form_is_read():
    assert _targets("[x](<a file.md>)") == ["a file.md"]


def test_an_escaped_parenthesis_does_not_close_the_target():
    assert _targets(r"[x](a\).md)") == [r"a\).md"]


def test_an_image_is_flagged():
    spans = scan_links("![alt](image.png)")
    assert len(spans) == 1
    assert spans[0].is_image is True
    assert spans[0].label == "alt"


def test_a_link_is_not_flagged_as_an_image():
    assert scan_links("[alt](a.md)")[0].is_image is False


def test_a_fenced_code_block_is_skipped():
    source = "text\n\n```\n[x](a.md)\n```\n\n[y](b.md)\n"
    assert _targets(source) == ["b.md"]


def test_a_tilde_fence_is_skipped():
    source = "~~~\n[x](a.md)\n~~~\n[y](b.md)\n"
    assert _targets(source) == ["b.md"]


def test_an_inline_code_span_is_skipped():
    assert _targets("`[x](a.md)` and [y](b.md)") == ["b.md"]


def test_spans_index_the_whole_construct():
    source = "go [docs](a.md) now"
    span = scan_links(source)[0]
    assert source[span.start:span.end] == "[docs](a.md)"


def test_an_image_span_includes_its_bang():
    source = "![alt](a.png)"
    span = scan_links(source)[0]
    assert source[span.start:span.end] == "![alt](a.png)"


def test_a_label_holding_brackets_is_read():
    assert _targets("[a [b] c](x.md)") == ["x.md"]


def test_a_target_resolves_against_its_pages_folder():
    assert resolve_target("Child.md", "Parent/Page.md") == "Parent/Child.md"
    assert resolve_target("Child.md", "Page.md") == "Child.md"


def test_dot_segments_and_empty_pieces_collapse():
    assert resolve_target("./a//b.md", "x/y/Page.md") == "x/y/a/b.md"
    assert resolve_target("../a.md", "x/y/Page.md") == "x/a.md"


def test_a_target_cannot_climb_above_the_root():
    assert resolve_target("../../a.md", "x/Page.md") == "a.md"
