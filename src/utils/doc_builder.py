"""PhoenixDocs builder utilities.

This module converts the PhoenixDocs Markdown collection into offline HTML
artifacts complete with a themed navigation experience suitable for the
Phoenix Web GUI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
import os
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title} · PhoenixDocs</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #05060a;
      --panel: #0c101c;
      --accent: #ff6bcb;
      --accent-soft: rgba(255, 107, 203, 0.2);
      --text: #f5f7ff;
      --muted: #8a92b2;
      --border: rgba(255, 255, 255, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: 'Segoe UI', Roboto, sans-serif;
      background: radial-gradient(circle at top, rgba(30, 64, 175, 0.35), transparent 55%), var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    header {{
      padding: 1.5rem 2rem;
      background: linear-gradient(135deg, rgba(255, 107, 203, 0.25), rgba(59, 130, 246, 0.25));
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
    }}
    header h1 {{ margin: 0; font-size: 1.8rem; letter-spacing: 0.08em; text-transform: uppercase; }}
    header p {{ margin: 0.35rem 0 0; color: var(--muted); }}
    main {{ display: grid; grid-template-columns: 320px 1fr; flex: 1; min-height: 0; }}
    nav {{
      padding: 2rem 1.5rem;
      background: linear-gradient(180deg, rgba(17, 24, 39, 0.85), rgba(17, 24, 39, 0.45));
      border-right: 1px solid var(--border);
      overflow-y: auto;
    }}
    nav h2 {{ margin-top: 0; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }}
    nav ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 0.75rem; }}
    nav a {{
      display: block;
      padding: 0.75rem 1rem;
      border-radius: 0.75rem;
      color: var(--text);
      text-decoration: none;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid transparent;
      transition: all 160ms ease;
    }}
    nav a.active {{
      border-color: var(--accent);
      background: var(--accent-soft);
      box-shadow: 0 0 20px rgba(255, 107, 203, 0.25);
    }}
    nav a:hover {{ border-color: var(--accent); transform: translateX(6px); }}
    article {{ padding: 2rem 3rem; overflow-y: auto; background: rgba(12, 16, 28, 0.8); }}
    article h1, article h2, article h3 {{ color: #ffffff; text-shadow: 0 2px 12px rgba(59, 130, 246, 0.35); }}
    article pre {{
      background: rgba(15, 23, 42, 0.9);
      border-radius: 0.75rem;
      padding: 1rem;
      border: 1px solid var(--border);
      overflow-x: auto;
    }}
    article table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1.5rem 0;
      background: rgba(15, 23, 42, 0.8);
      border-radius: 0.75rem;
      overflow: hidden;
    }}
    article th, article td {{
      border: 1px solid var(--border);
      padding: 0.75rem 1rem;
      text-align: left;
    }}
    article blockquote {{
      margin: 1.5rem 0;
      padding: 1rem 1.5rem;
      border-left: 4px solid var(--accent);
      background: rgba(59, 130, 246, 0.12);
      border-radius: 0 0.75rem 0.75rem 0;
      color: var(--muted);
    }}
    footer {{
      padding: 1rem 2rem;
      font-size: 0.85rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
      background: rgba(5, 6, 10, 0.85);
    }}
    @media (max-width: 900px) {{
      main {{ grid-template-columns: 1fr; }}
      nav {{ position: sticky; top: 0; z-index: 5; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>PhoenixDocs</h1>
    <p>BootForge Phoenix Key · Offline Field Manual</p>
  </header>
  <main>
    <nav>
      <h2>Guides</h2>
      <ul>
        {nav_items}
      </ul>
    </nav>
    <article>
      {content}
    </article>
  </main>
  <footer>
    Phoenix Key build {build_version} · Generated {build_timestamp}
  </footer>
</body>
</html>
"""


class SimpleMarkdownRenderer:
    """Lightweight Markdown renderer tailored for PhoenixDocs."""

    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")
    ul_pattern = re.compile(r"^[-*+]\s+(.*)$")
    ol_pattern = re.compile(r"^\d+\.\s+(.*)$")
    table_divider_pattern = re.compile(r"^\s*[:\-\|\s]+$")

    def render(self, markdown_text: str) -> str:
        lines = markdown_text.splitlines()
        html_parts: List[str] = []
        paragraph_buffer: List[str] = []
        in_code_block = False
        code_language = ""
        code_lines: List[str] = []
        index = 0
        total_lines = len(lines)

        while index < total_lines:
            line = lines[index]
            stripped = line.strip()

            if in_code_block:
                if stripped.startswith("```"):
                    html_parts.append(self._render_code_block(code_lines, code_language))
                    in_code_block = False
                    code_lines = []
                    code_language = ""
                else:
                    code_lines.append(line)
                index += 1
                continue

            if stripped.startswith("```"):
                if paragraph_buffer:
                    html_parts.append(self._render_paragraph(paragraph_buffer))
                    paragraph_buffer = []
                in_code_block = True
                code_language = stripped[3:].strip()
                index += 1
                continue

            if not stripped:
                if paragraph_buffer:
                    html_parts.append(self._render_paragraph(paragraph_buffer))
                    paragraph_buffer = []
                index += 1
                continue

            # Tables
            if stripped.startswith("|") and "|" in stripped[1:]:
                if paragraph_buffer:
                    html_parts.append(self._render_paragraph(paragraph_buffer))
                    paragraph_buffer = []

                table_lines: List[str] = []
                while index < total_lines:
                    row = lines[index].strip()
                    if not row.startswith("|"):
                        break
                    table_lines.append(row)
                    index += 1
                html_parts.append(self._render_table(table_lines))
                continue

            heading_match = self.heading_pattern.match(stripped)
            if heading_match:
                if paragraph_buffer:
                    html_parts.append(self._render_paragraph(paragraph_buffer))
                    paragraph_buffer = []
                level = len(heading_match.group(1))
                title = self._format_inline(heading_match.group(2))
                html_parts.append(f"<h{level}>{title}</h{level}>")
                index += 1
                continue

            ul_match = self.ul_pattern.match(stripped)
            if ul_match:
                if paragraph_buffer:
                    html_parts.append(self._render_paragraph(paragraph_buffer))
                    paragraph_buffer = []
                items, index = self._collect_list(lines, index, ordered=False)
                html_parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>")
                continue

            ol_match = self.ol_pattern.match(stripped)
            if ol_match:
                if paragraph_buffer:
                    html_parts.append(self._render_paragraph(paragraph_buffer))
                    paragraph_buffer = []
                items, index = self._collect_list(lines, index, ordered=True)
                html_parts.append("<ol>" + "".join(f"<li>{item}</li>" for item in items) + "</ol>")
                continue

            paragraph_buffer.append(stripped)
            index += 1

        if in_code_block:
            html_parts.append(self._render_code_block(code_lines, code_language))

        if paragraph_buffer:
            html_parts.append(self._render_paragraph(paragraph_buffer))

        return "\n".join(html_parts)

    def _render_paragraph(self, lines: List[str]) -> str:
        text = " ".join(lines)
        return f"<p>{self._format_inline(text)}</p>"

    def _render_code_block(self, lines: List[str], language: str) -> str:
        code = "\n".join(lines)
        cls = f" class=\"language-{escape(language)}\"" if language else ""
        return f"<pre><code{cls}>{escape(code)}</code></pre>"

    def _render_table(self, rows: List[str]) -> str:
        parsed_rows = [self._split_table_row(row) for row in rows if row.strip()]
        if not parsed_rows:
            return ""

        body_rows = parsed_rows
        header_cells: List[str] | None = None

        if len(parsed_rows) > 1 and all(
            self.table_divider_pattern.match(cell.strip()) for cell in parsed_rows[1]
        ):
            header_cells = [self._format_inline(cell.strip("-:")) for cell in parsed_rows[0]]
            body_rows = parsed_rows[2:]
        else:
            header_cells = [self._format_inline(cell) for cell in parsed_rows[0]]
            body_rows = parsed_rows[1:]

        header_html = "".join(f"<th>{cell}</th>" for cell in header_cells)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{self._format_inline(cell)}</td>" for cell in row) + "</tr>"
            for row in body_rows
        )
        return f"<table><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"

    def _split_table_row(self, row: str) -> List[str]:
        parts = [part.strip() for part in row.strip().strip("|").split("|")]
        return parts

    def _collect_list(self, lines: List[str], start: int, *, ordered: bool) -> tuple[List[str], int]:
        items: List[str] = []
        index = start
        pattern = self.ol_pattern if ordered else self.ul_pattern
        total_lines = len(lines)

        while index < total_lines:
            stripped = lines[index].strip()
            match = pattern.match(stripped)
            if not match:
                break
            item_text = match.group(1)
            items.append(self._format_inline(item_text))
            index += 1
        return items, index

    def _format_inline(self, text: str) -> str:
        escaped = escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"__(.+?)__", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
        escaped = re.sub(r"_(.+?)_", r"<em>\1</em>", escaped)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\[(.+?)\]\((.+?)\)", r"<a href=\"\2\">\1</a>", escaped)
        return escaped


@dataclass
class DocumentMeta:
    """Metadata describing a PhoenixDocs entry."""

    title: str
    source_path: Path
    output_path: Path

    @property
    def slug(self) -> str:
        return self.output_path.stem


class PhoenixDocsBuilder:
    """Build PhoenixDocs HTML artefacts from Markdown sources."""

    def __init__(
        self,
        source_dir: Path | str,
        output_dir: Path | str,
        *,
        template: Optional[str] = None,
        markdown_engine: Optional[SimpleMarkdownRenderer] = None,
        build_version: str = "1.0.0",
    ) -> None:
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.template = template or DEFAULT_TEMPLATE
        self.markdown = markdown_engine or SimpleMarkdownRenderer()
        self.build_version = build_version
        self.build_timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def build(self) -> Dict[str, List[Dict[str, str]]]:
        """Render Markdown sources into HTML documents.

        Returns a manifest dictionary describing the built documents.
        """
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        markdown_files = sorted(self.source_dir.rglob("*.md"))
        if not markdown_files:
            raise FileNotFoundError("No Markdown files found in PhoenixDocs source directory")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        docs_meta: List[DocumentMeta] = []
        for md_path in markdown_files:
            rel = md_path.relative_to(self.source_dir)
            html_path = self.output_dir / rel.with_suffix(".html")
            html_path.parent.mkdir(parents=True, exist_ok=True)

            raw_markdown = md_path.read_text(encoding="utf-8")
            title = self._extract_title(raw_markdown) or md_path.stem.replace("_", " ").title()
            rendered_html = self.markdown.render(raw_markdown)

            meta = DocumentMeta(title=title, source_path=md_path, output_path=html_path)
            docs_meta.append(meta)

            nav_items = self._render_nav(
                docs_meta,
                active_slug=meta.slug,
                current_output=html_path,
            )
            html_content = self._wrap_html(title, rendered_html, nav_items)
            html_path.write_text(html_content, encoding="utf-8")

        manifest = {
            "documents": [
                {
                    "title": meta.title,
                    "source": str(meta.source_path.relative_to(self.source_dir)),
                    "html": str(meta.output_path.relative_to(self.output_dir)),
                }
                for meta in docs_meta
            ]
        }

        manifest_path = self.output_dir / "phoenix_docs_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        self._write_index(docs_meta)
        return manifest

    def _wrap_html(self, title: str, content: str, nav_items: str) -> str:
        return self.template.format(
            title=title,
            content=content,
            nav_items=nav_items,
            build_version=self.build_version,
            build_timestamp=self.build_timestamp,
        )

    def _render_nav(
        self,
        docs: Iterable[DocumentMeta],
        *,
        active_slug: str,
        current_output: Path,
    ) -> str:
        items = []
        for meta in docs:
            rel_path = os.path.relpath(meta.output_path, start=current_output.parent)
            css_class = "active" if meta.slug == active_slug else ""
            items.append(f'<li><a href="{rel_path}" class="{css_class}">{meta.title}</a></li>')
        return "\n        ".join(items)

    def _write_index(self, docs_meta: List[DocumentMeta]) -> None:
        # Build a simple index page linking to all docs.
        index_path = self.output_dir / "index.html"
        links = "\n".join(
            f'<li><a href="{os.path.relpath(meta.output_path, start=index_path.parent)}">{meta.title}</a></li>'
            for meta in docs_meta
        )
        content = f"<h1>Welcome to PhoenixDocs</h1><p>Select a guide:</p><ul>{links}</ul>"
        nav = self._render_nav(
            docs_meta,
            active_slug="",
            current_output=index_path,
        )
        index_html = self._wrap_html("PhoenixDocs", content, nav)
        index_path.write_text(index_html, encoding="utf-8")

    @staticmethod
    def _extract_title(markdown_text: str) -> Optional[str]:
        for line in markdown_text.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None


__all__ = ["PhoenixDocsBuilder"]
