import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.pdf_reader import extract_text_from_pdf

PDF_PATH = os.path.join(os.path.dirname(__file__), "sample_resume.pdf")


def test_pdf_extraction():
    result = extract_text_from_pdf(PDF_PATH)

    # check no error occurred
    assert result["error"] is None, f"PDF extraction failed: {result['error']}"

    # check we got at least one page
    assert result["page_count"] >= 1, "PDF has no pages"

    # check we got actual text, not an empty string
    assert len(result["full_text"].strip()) > 100, "Extracted text is too short — is this a scanned PDF?"

    print(f"\n✓ Pages found: {result['page_count']}")
    print(f"✓ Total characters extracted: {len(result['full_text'])}")
    print(f"\n── First 500 characters of extracted text ──")
    print(result["full_text"][:500])
    print("────────────────────────────────────────────")

    for p in result["pages"]:
        print(f"  Page {p['page_number']}: {p['char_count']} chars")


if __name__ == "__main__":
    test_pdf_extraction()