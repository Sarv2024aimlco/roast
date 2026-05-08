import httpx
from bs4 import BeautifulSoup

LEVELS_BASE = "https://www.levels.fyi/companies/{company}/salaries/{role}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Maps our internal role names to Levels.fyi URL slugs
ROLE_SLUG_MAP = {
    "SDE1": "software-engineer",
    "SDE2": "software-engineer",
    "Senior SDE": "software-engineer",
    "Full Stack Engineer": "software-engineer",
    "Backend Engineer": "software-engineer",
    "ML Engineer": "machine-learning-engineer",
    "AI Engineer": "machine-learning-engineer",
    "Data Engineer": "data-engineer",
    "Data Scientist": "data-scientist",
    "Data Analyst": "data-analyst",
    "DevOps / SRE": "site-reliability-engineer",
    "Product Manager": "product-manager",
}

# Maps company names to Levels.fyi URL slugs
COMPANY_SLUG_MAP = {
    "Google": "google",
    "Microsoft": "microsoft",
    "Amazon": "amazon",
    "Meta": "meta",
    "Apple": "apple",
    "Flipkart": "flipkart",
    "Swiggy": "swiggy",
    "Razorpay": "razorpay",
    "Zepto": "zepto",
    "PhonePe": "phonepe",
}


async def fetch_levels_salary(company: str, role: str) -> dict:
    """
    Fetch salary data for a company + role from Levels.fyi.
    Returns structured salary data or empty dict if unavailable.
    """
    company_slug = COMPANY_SLUG_MAP.get(company)
    role_slug = ROLE_SLUG_MAP.get(role)

    if not company_slug or not role_slug:
        return {}

    url = LEVELS_BASE.format(company=company_slug, role=role_slug)

    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
    except Exception:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    return _extract_salary_data(soup, company, role, url)


def _extract_salary_data(soup: BeautifulSoup, company: str, role: str, url: str) -> dict:
    """
    Extract salary table from parsed HTML.
    Returns structured dict with levels and compensation ranges.
    """
    result = {
        "company": company,
        "role": role,
        "source_url": url,
        "levels": [],
        "raw_text": "",
    }

    # Extract all visible text from the page — Gemma 4 26B will process this
    # We don't need to parse every table cell perfectly
    # The LLM is better at extracting structured data from messy text than regex
    main_content = soup.find("main") or soup.find("body")
    if main_content:
        result["raw_text"] = main_content.get_text(separator=" ", strip=True)[:3000]

    # Also try to extract the salary table directly if structure is clean
    rows = soup.select("tr")
    for row in rows:
        cells = row.select("td")
        if len(cells) >= 3:
            level_text = cells[0].get_text(strip=True)
            total_text = cells[1].get_text(strip=True)
            base_text = cells[2].get_text(strip=True)
            if level_text and total_text:
                result["levels"].append({
                    "level": level_text,
                    "total": total_text,
                    "base": base_text,
                })

    return result
