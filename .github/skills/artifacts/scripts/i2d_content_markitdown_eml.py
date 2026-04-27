"""Dedicated EML parsing helpers for i2d_content_markitdown_email."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import i2d_content_markitdown_mail_parts as _mail_parts


_PLAIN_TEXT_EXTS = (".json", ".csv", ".tsv", ".xml", ".yaml", ".yml")


def _process_attachment_part(
    part: Any,
    content_type: str,
    filename: str | None,
    payload: bytes | None,
    attachment_count: int,
) -> tuple[str, int]:
    """Process a single attachment part; return (attachment_block, updated_count)."""
    attachment_count += 1
    safe_name = filename or f"attachment_{attachment_count}"
    digest = hashlib.sha256(payload or b"").hexdigest()  # type: ignore[arg-type]
    meta = [
        f"- name: {safe_name}",
        f"- content_type: {content_type}",
        f"- size_bytes: {len(payload or b'')}",
        f"- sha256: {digest}",
    ]
    attachment_text = _get_attachment_text(content_type, safe_name, part, payload)
    if attachment_text:
        return "\n".join(
            [
                f"### Attachment: {safe_name}",
                *meta,
                "",
                "```text",
                attachment_text,
                "```",
            ]
        ), attachment_count
    return "\n".join([f"### Attachment: {safe_name}", *meta]), attachment_count


def _is_supported_text_type(content_type: str) -> bool:
    """Check if the content type is plain or HTML text."""
    return content_type in {"text/plain", "text/html"}


def _extract_part_metadata(part: Any) -> tuple[str, str, str | None, bytes | None]:
    """Extract metadata from an email part."""
    content_type = part.get_content_type()  # type: ignore[attr-defined]
    disposition = (part.get_content_disposition() or "").lower()  # type: ignore[attr-defined]
    filename = part.get_filename()  # type: ignore[attr-defined]
    payload = part.get_payload(decode=True)  # type: ignore[attr-defined]
    return content_type, disposition, filename, payload


def _determine_is_attachment(disposition: str, filename: str | None) -> bool:
    """Determine if part should be treated as attachment."""
    return disposition == "attachment" or bool(filename)


def _process_text_part(
    part: Any, content_type: str, plain_parts: list[str], html_parts: list[str]
) -> None:
    """Process text part and add to appropriate list."""
    if not _is_supported_text_type(content_type):
        return
    text = _mail_parts.decode_message_part(part)
    if not text:
        return
    if content_type == "text/plain":
        plain_parts.append(text)
    elif content_type == "text/html":
        html_parts.append(text)


def _process_eml_parts(
    msg: Any,
) -> tuple[list[str], list[str], list[str]]:
    """Iterate message parts; return (plain_parts, html_parts, attachment_blocks)."""
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachment_blocks: list[str] = []
    attachment_count = 0

    parts = msg.walk() if msg.is_multipart() else [msg]  # type: ignore[union-attr]
    for part in parts:
        if part.is_multipart():  # type: ignore[attr-defined]
            continue

        content_type, disposition, filename, payload = _extract_part_metadata(part)
        is_attachment = _determine_is_attachment(disposition, filename)

        if not is_attachment:
            _process_text_part(part, content_type, plain_parts, html_parts)
            continue

        block, attachment_count = _process_attachment_part(
            part, content_type, filename, payload, attachment_count
        )
        attachment_blocks.append(block)

    return plain_parts, html_parts, attachment_blocks


def _get_attachment_text(
    content_type: str, safe_name: str, part: Any, payload: bytes | None
) -> str:
    """Return decoded text for inline attachment preview if applicable."""
    if content_type.startswith("text/"):
        return _mail_parts.decode_message_part(part).strip()
    if safe_name.lower().endswith(_PLAIN_TEXT_EXTS):
        try:
            return (payload or b"").decode("utf-8", errors="replace").strip()
        except (UnicodeDecodeError, ValueError):
            return ""
    return ""


def _build_attachment_blocks(
    plain_parts: list[str], html_parts: list[str], attachment_blocks: list[str]
) -> str:
    """Build email body and attachment sections."""
    body_sections: list[str] = []
    if plain_parts:
        body_sections.append("\n\n".join(plain_parts))
    elif html_parts:
        body_sections.extend(
            stripped
            for html in html_parts
            if (stripped := _mail_parts.html_to_text(html))
        )

    body = "\n\n".join(body_sections).strip() or "(no readable body)"
    attachment_section = (
        "\n\n## Email Attachments\n\n" + "\n\n".join(attachment_blocks)
        if attachment_blocks
        else ""
    )
    return body + attachment_section


def extract_eml(path: Path, *, file_facts_fn) -> tuple[str, str, str]:
    """Extract email headers, body, and attachment metadata from an EML file."""
    import email as _email_lib
    from email import policy as _email_policy

    try:
        with path.open("rb") as fh:
            msg = _email_lib.message_from_binary_file(fh, policy=_email_policy.default)

        headers_md = (
            f"- **From**: {str(msg.get('From', ''))}\n"
            f"- **To**: {str(msg.get('To', ''))}\n"
            f"- **Subject**: {str(msg.get('Subject', ''))}\n"
            f"- **Date**: {str(msg.get('Date', ''))}"
        )
        plain_parts, html_parts, attachment_blocks = _process_eml_parts(msg)
        body_and_attachments = _build_attachment_blocks(
            plain_parts, html_parts, attachment_blocks
        )

        content = (
            f"## File Facts\n\n{file_facts_fn(path)}\n\n"
            f"## Email Headers\n\n{headers_md}\n\n"
            f"## Email Body\n\n{body_and_attachments}"
        )
        return content, "eml-parser", "ok"
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return (
            f"## File Facts\n\n{file_facts_fn(path)}\n\nEML parsing failed: {exc}",
            "eml-parser",
            "error",
        )
