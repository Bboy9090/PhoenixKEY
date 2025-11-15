"""Tests for the PhoenixDocs builder utilities."""

from pathlib import Path
import json

import pytest

from src.utils.doc_builder import PhoenixDocsBuilder


@pytest.fixture()
def sample_docs(tmp_path: Path) -> Path:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "alpha.md").write_text("# Alpha\n\nAlpha body.", encoding="utf-8")
    (docs_dir / "beta.md").write_text("# Beta\n\nBeta body.", encoding="utf-8")
    return docs_dir


def test_build_generates_html_and_manifest(sample_docs: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "html"
    builder = PhoenixDocsBuilder(sample_docs, output_dir, build_version="9.9.9")

    manifest = builder.build()

    # Verify manifest content
    assert "documents" in manifest
    assert len(manifest["documents"]) == 2

    # Ensure HTML files exist and contain headings
    for entry in manifest["documents"]:
        html_path = output_dir / entry["html"]
        assert html_path.exists()
        html = html_path.read_text(encoding="utf-8")
        assert entry["title"] in html
        assert "PhoenixDocs" in html  # Themed template applied

    # Manifest file saved to disk
    manifest_path = output_dir / "phoenix_docs_manifest.json"
    assert manifest_path.exists()
    saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved_manifest == manifest


def test_missing_source_directory_raises(tmp_path: Path) -> None:
    output_dir = tmp_path / "html"
    missing_source = tmp_path / "missing"
    builder = PhoenixDocsBuilder(missing_source, output_dir)

    with pytest.raises(FileNotFoundError):
        builder.build()
