"""Shared text-screen formatting helpers for Brave's full-scene command views."""

from textwrap import wrap


SCREEN_WIDTH = 64


def section_rule(title, width=SCREEN_WIDTH):
    """Return a compact section divider."""

    label = str(title or "").strip().upper() or "SECTION"
    fill = max(8, width - len(label) - 5)
    return f"--- {label} " + ("-" * fill)


def wrap_text(text, *, width=SCREEN_WIDTH, indent="", subsequent_indent=None):
    """Wrap one text block into display-ready lines."""

    if text is None:
        return []

    value = str(text).strip()
    if not value:
        return [indent.rstrip()]

    return wrap(
        value,
        width=width,
        initial_indent=indent,
        subsequent_indent=subsequent_indent if subsequent_indent is not None else indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def format_pairs(pairs, *, width=SCREEN_WIDTH, indent="  ", label_width=14):
    """Format aligned label/value rows with wrapping."""

    rows = []
    valid_pairs = [(label, value) for label, value in pairs if value not in (None, "")]
    if not valid_pairs:
        return rows

    computed_width = max(len(str(label)) for label, _ in valid_pairs)
    label_width = max(label_width, computed_width)

    for label, value in valid_pairs:
        prefix = f"{indent}{str(label):<{label_width}} "
        rows.extend(
            wrap_text(
                value,
                width=width,
                indent=prefix,
                subsequent_indent=" " * len(prefix),
            )
        )
    return rows


def format_entry(title, *, details=None, summary=None, width=SCREEN_WIDTH, indent="  "):
    """Format a compact item/quest/order block."""

    lines = [f"{indent}{title}"]

    for detail in details or []:
        if detail:
            lines.extend(wrap_text(detail, width=width, indent=indent + "  "))

    if summary:
        lines.extend(wrap_text(summary, width=width, indent=indent + "  "))

    return lines


def render_screen(title, *, subtitle=None, meta=None, sections=None, width=SCREEN_WIDTH):
    """Render a full text-screen with a shared Brave structure."""

    lines = [f"|w{title}|n"]

    subtitle_lines = subtitle if isinstance(subtitle, (list, tuple)) else [subtitle] if subtitle else []
    for line in subtitle_lines:
        if line == "":
            lines.append("")
        else:
            lines.extend(wrap_text(line, width=width))

    meta_parts = [part for part in (meta or []) if part]
    if meta_parts:
        lines.extend(wrap_text(" | ".join(meta_parts), width=width))

    for section_title, content in sections or []:
        if not content:
            continue
        lines.append("")
        lines.append(section_rule(section_title, width=width))
        if isinstance(content, str):
            lines.extend(wrap_text(content, width=width, indent="  "))
            continue
        lines.extend(content)

    return "\n".join(lines)
