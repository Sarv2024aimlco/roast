import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.pdf_reader import extract_text_from_pdf, extract_links, verify_link

PDF_PATH = os.path.join(os.path.dirname(__file__), "sample_resume.pdf")


def test_full_extraction():
    result = extract_text_from_pdf(PDF_PATH)
    assert result["error"] is None, f"Error: {result['error']}"
    assert result["is_valid"], f"Validation failed: {result['validation_error']}"
    print(f"\n✓ Pages: {result['page_count']}")
    print(f"✓ Chars: {len(result['full_text'])}")
    print(f"✓ Valid: {result['is_valid']}")
    print(f"\n── Cleaned text (first 400 chars) ──")
    print(result["full_text"][:400])


def test_link_extraction():
    links = extract_links(PDF_PATH)
    print(f"\n✓ All URLs found: {links['all_urls']}")
    print(f"✓ LinkedIn: {links['linkedin']}")
    print(f"✓ GitHub:   {links['github']}")


def test_link_verification():
    # only run if we found links
    links = extract_links(PDF_PATH)
    for url in [links["linkedin"], links["github"]]:
        if url:
            result = verify_link(url)
            print(f"\n✓ {url}")
            print(f"  reachable={result['reachable']}, status={result['status_code']}")


if __name__ == "__main__":
    test_full_extraction()
    test_link_extraction()
    test_link_verification()