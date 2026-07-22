import pytest
from services.parser import (
    _check_mime,
    _append_links,
    parse_resume,
)


def test_check_mime_valid_pdf_magic():
    valid_pdf_bytes = b"%PDF-1.4 header bytes..."
    # Should not raise exception
    _check_mime("resume.pdf", valid_pdf_bytes, "application/pdf")


def test_check_mime_invalid_pdf_magic():
    invalid_pdf_bytes = b"NOT_A_PDF_HEADER"
    with pytest.raises(ValueError, match="does not appear to be a valid PDF"):
        _check_mime("resume.pdf", invalid_pdf_bytes, "application/pdf")


def test_check_mime_valid_docx_magic():
    valid_docx_bytes = b"PK\x03\x04zip_header_bytes..."
    # Should not raise exception
    _check_mime("resume.docx", valid_docx_bytes, "application/octet-stream")


def test_parse_resume_unsupported_extensions():
    with pytest.raises(ValueError, match="Legacy .doc format is not supported"):
        parse_resume("old_resume.doc", b"dummy")

    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_resume("image.png", b"dummy")


def test_append_links():
    base = "Resume content line 1\nResume content line 2"
    urls = ["https://github.com/ayush", "https://linkedin.com/in/ayush"]
    result = _append_links(base, urls)

    assert "Hyperlinks:" in result
    assert "https://github.com/ayush" in result
    assert "https://linkedin.com/in/ayush" in result

    # Should not duplicate existing URLs
    already_present = "Resume content with https://github.com/ayush link"
    result2 = _append_links(already_present, urls)
    assert result2.count("https://github.com/ayush") == 1
