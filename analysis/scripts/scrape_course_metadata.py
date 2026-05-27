"""
scrape_course_metadata.py
-------------------------
Scrapes Wikipedia for course metadata: type, country, yardage, par, year, etc.
Includes manual override map for ambiguous course names.

Usage:
    python scrape_course_metadata.py              # scrape missing courses
    python scrape_course_metadata.py --force      # rescrape everything
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

import time
from collections import deque

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
META_PATH = DATA_DIR / "course_metadata.json"
META_PATH.parent.mkdir(parents=True, exist_ok=True)

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "caddie-desk/1.0 (caddiedesk.com)"}

# Manual overrides for courses with disambiguation issues or known data
MANUAL_OVERRIDES = {
    "TPC River Highlands": {"wiki_title": "TPC_River_Highlands"},
    "TPC Southwind": {"wiki_title": "TPC_Southwind"},
    "TPC Deere Run": {"wiki_title": "TPC_Deere_Run"},
    "TPC Scottsdale": {"wiki_title": "TPC_Scottsdale"},
    "TPC Sawgrass": {"wiki_title": "TPC_at_Sawgrass"},
    "Royal Liverpool": {"wiki_title": "Royal_Liverpool_Golf_Club"},
    "Royal Birkdale": {"wiki_title": "Royal_Birkdale_Golf_Club"},
    "Royal Troon": {"wiki_title": "Royal_Troon_Golf_Club"},
    "Royal Portrush": {"wiki_title": "Royal_Portrush_Golf_Club"},
    "Royal St George's": {"wiki_title": "Royal_St_George's_Golf_Club"},
    "St Andrews": {"wiki_title": "Old_Course_at_St_Andrews"},
    "Old Course at St Andrews": {"wiki_title": "Old_Course_at_St_Andrews"},
    # Add more as you spot them
}

# Country → continent mapping for the simple categorisation
COUNTRY_REGIONS = {
    "United States": "USA",
    "USA": "USA",
    "England": "UK",
    "Scotland": "UK",
    "Wales": "UK",
    "Northern Ireland": "UK",
    "Republic of Ireland": "UK",
    "Ireland": "UK",
    "Spain": "Europe",
    "France": "Europe",
    "Germany": "Europe",
    "Italy": "Europe",
    "Portugal": "Europe",
    "Netherlands": "Europe",
    "Switzerland": "Europe",
    "Australia": "Asia/Pacific",
    "Japan": "Asia/Pacific",
    "South Korea": "Asia/Pacific",
    "Singapore": "Asia/Pacific",
    "Malaysia": "Asia/Pacific",
    "China": "Asia/Pacific",
    "United Arab Emirates": "Middle East",
    "Saudi Arabia": "Middle East",
    "South Africa": "Africa",
    "Canada": "USA",
    "Mexico": "Other",
    "Bahamas": "Other",
    "Bermuda": "Other",
    "Dominican Republic": "Other",
    "Puerto Rico": "Other",
}

# Course type keywords found in Wikipedia text
COURSE_TYPE_KEYWORDS = {
    "links": ["links", "links-style", "links course"],
    "parkland": ["parkland", "parkland course"],
    "heathland": ["heathland", "heath"],
    "desert": ["desert", "desert course"],
    "coastal": ["coastal", "seaside", "ocean", "cliff"],
    "stadium": ["stadium course"],
    "mountain": ["mountain", "elevation"],
}

# Rate limit: max 30 requests per minute (very conservative)
_request_times = deque()
_RATE_LIMIT = 30
_RATE_WINDOW = 60  # seconds

def _rate_limited_get(url, **kwargs):
    """Wraps requests.get with proactive rate limiting and 429 handling."""
    now = time.time()
    
    while _request_times and now - _request_times[0] > _RATE_WINDOW:
        _request_times.popleft()
    
    if len(_request_times) >= _RATE_LIMIT:
        wait = _RATE_WINDOW - (now - _request_times[0]) + 0.5
        print(f"    ⏱ Rate limit window — pausing {wait:.1f}s")
        time.sleep(wait)
    
    _request_times.append(time.time())
    response = requests.get(url, **kwargs)
    
    # If we got a 429 despite rate limiting, back off hard
    if response.status_code == 429:
        print(f"    ⏱ Got 429 — backing off 60s")
        time.sleep(60)
    
    return response

def search_wiki(query: str, limit: int = 5) -> list[str]:
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
    }
    for attempt in range(3):
        try:
            r = _rate_limited_get(WIKI_API, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return [h["title"] for h in r.json().get("query", {}).get("search", [])]
        except (requests.RequestException, ValueError) as e:
            print(f"    Search retry {attempt+1}/3 for '{query}': {e}")
            time.sleep(3)
    return []


def get_wiki_page(title: str) -> Optional[dict]:
    params = {
        "action": "parse",
        "format": "json",
        "page": title,
        "prop": "wikitext|properties",
    }
    for attempt in range(3):
        try:
            r = _rate_limited_get(WIKI_API, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.json().get("parse", {})
        except (requests.RequestException, ValueError) as e:
            print(f"    Page retry {attempt+1}/3 for '{title}': {e}")
            time.sleep(3)
    return None


def extract_field(wikitext: str, *field_names) -> Optional[str]:
    """Extract a field from the Wikipedia infobox by trying multiple field names."""
    for name in field_names:
        # Match the field name, then capture to end of line
        # (allowing internal pipes for templates like {{convert|...}})
        pattern = rf"\|\s*{re.escape(name)}\s*=\s*([^\n]+)"
        match = re.search(pattern, wikitext, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            
            # Handle {{convert|N|unit}} templates → "N unit"
            value = re.sub(
                r"\{\{convert\s*\|\s*([\d,.]+)\s*\|\s*(\w+)[^}]*\}\}",
                r"\1 \2",
                value,
                flags=re.IGNORECASE,
            )
            
            # Clean wikilinks
            value = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", value)
            
            # Strip citation refs
            value = re.sub(r"<ref[^>]*>.*?</ref>", "", value, flags=re.DOTALL)
            value = re.sub(r"<ref[^/]*/>", "", value)
            
            # Strip HTML tags
            value = re.sub(r"<[^>]+>", "", value)
            
            # Remove any remaining templates
            value = re.sub(r"\{\{[^}]+\}\}", "", value)
            
            # Normalise whitespace
            value = re.sub(r"\s+", " ", value).strip()
            
            if value and value != "—":
                return value
    return None

def _extract_first_paragraph(wikitext: str) -> str:
    """Get just the lead paragraph (before any section header)."""
    # Skip past infobox/templates at the top
    text = wikitext
    
    # Remove templates {{...}}
    while "{{" in text:
        start = text.find("{{")
        depth = 1
        i = start + 2
        while i < len(text) and depth > 0:
            if text[i:i+2] == "{{":
                depth += 1
                i += 2
            elif text[i:i+2] == "}}":
                depth -= 1
                i += 2
            else:
                i += 1
        text = text[:start] + text[i:]
    
    # Take everything up to first section header
    match = re.search(r"^==", text, re.MULTILINE)
    if match:
        text = text[:match.start()]
    
    # Strip wiki links and refs
    text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    
    return text.strip()


def parse_yardage(value: str) -> Optional[int]:
    """Extract numeric yardage from messy text like '7,233 yd' or '7233 yards'."""
    if not value:
        return None
    # Find first number with optional commas
    match = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)", value.replace(",", ""))
    if match:
        try:
            n = int(match.group(1))
            if 5000 <= n <= 9000:  # sanity check
                return n
        except ValueError:
            pass
    return None


def parse_par(value: str) -> Optional[int]:
    """Extract par from text like '72' or 'Par 71'."""
    if not value:
        return None
    match = re.search(r"\b(6[8-9]|7[0-5])\b", value)
    if match:
        return int(match.group(1))
    return None


def parse_year(value: str) -> Optional[int]:
    """Extract a 4-digit year from text."""
    if not value:
        return None
    match = re.search(r"\b(18\d{2}|19\d{2}|20[0-2]\d)\b", value)
    if match:
        return int(match.group(1))
    return None


def parse_country(value: str) -> Optional[str]:
    """Identify country from location/country text."""
    if not value:
        return None
    for country in COUNTRY_REGIONS.keys():
        if country.lower() in value.lower():
            return country
    return None

def identify_course_type(wikitext: str) -> list[str]:
    """Find course types from the lead paragraph only."""
    lead = _extract_first_paragraph(wikitext).lower()
    
    types_found = []
    for type_name, keywords in COURSE_TYPE_KEYWORDS.items():
        for kw in keywords:
            # Word-boundary match to avoid substring false positives
            if re.search(rf"\b{re.escape(kw)}\b", lead):
                types_found.append(type_name)
                break
    return types_found

def normalize_course_name_variants(course_name: str) -> list[str]:
    """Generate search variants for a course name."""
    variants = [course_name]
    
    # Common abbreviation expansions
    replacements = [
        (" GC", " Golf Club"),
        (" G.C.", " Golf Club"),
        (" CC", " Country Club"),
        (" C.C.", " Country Club"),
        (" G&CC", " Golf and Country Club"),
        (" G&CC", " Golf & Country Club"),
        (" G & CC", " Golf and Country Club"),
        (" GL", " Golf Links"),
        (" GR", " Golf Resort"),
    ]
    
    for abbr, full in replacements:
        if abbr in course_name:
            variants.append(course_name.replace(abbr, full))
    
    # Strip parentheticals like "(South)" or "(Champion)"
    no_paren = re.sub(r"\s*\([^)]+\)\s*", " ", course_name).strip()
    if no_paren != course_name and no_paren:
        variants.append(no_paren)
        # Also try expansions on the simplified name
        for abbr, full in replacements:
            if abbr in no_paren:
                variants.append(no_paren.replace(abbr, full))
    
    # Add "golf course" suffix variants
    base_variants = list(variants)
    for v in base_variants:
        if "golf" not in v.lower() and "club" not in v.lower():
            variants.append(f"{v} Golf Club")
            variants.append(f"{v} Golf Course")
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def scrape_course(course_name: str) -> dict:
    """Look up a course on Wikipedia and extract metadata."""
    result = {
        "course_name": course_name,
        "wiki_title": None,
        "wiki_status": "not_found",
        "country": None,
        "region": None,
        "yardage": None,
        "par": None,
        "designed_year": None,
        "designer": None,
        "course_types": [],
        "coastal": None,
    }
    
    # Use override if available
    if course_name in MANUAL_OVERRIDES:
        wiki_title = MANUAL_OVERRIDES[course_name].get("wiki_title")
        page = get_wiki_page(wiki_title)
        if page:
            wikitext = page.get("wikitext", {}).get("*", "")
            if wikitext and _is_golf_page(wikitext, wiki_title):
                return _extract_from_wikitext(course_name, wiki_title, wikitext)
        return result
    
    # Try the most natural variant first
    variants = normalize_course_name_variants(course_name)
    
    for variant in variants:
        candidates = search_wiki(variant)
        if not candidates:
            continue
        
        # Only try the top candidate per variant
        wiki_title = candidates[0]
        page = get_wiki_page(wiki_title)
        if not page:
            continue
        
        wikitext = page.get("wikitext", {}).get("*", "")
        if not wikitext or not _is_golf_page(wikitext, wiki_title):
            continue
        
        return _extract_from_wikitext(course_name, wiki_title, wikitext)
    
    return result


def _is_golf_page(wikitext: str, title: str = "") -> bool:
    """Quick check that this page is actually a golf course."""
    text = wikitext.lower()
    title_lower = title.lower() if title else ""
    
    # Reject tournament/event pages
    tournament_indicators = ["championship", "open", "invitational", "tournament", 
                            "playoff", "presidents cup", "ryder cup"]
    if any(t in title_lower for t in tournament_indicators):
        # Allow only if it's clearly a club name like "Royal Liverpool Golf Club"
        if "golf club" not in title_lower and "country club" not in title_lower:
            return False
    
    # Must have golf-course indicators
    return any(term in text[:3000] for term in [
        "infobox golf facility",
        "infobox golf course",
        "golf course in",
        "golf club in",
        "private golf",
    ])


def _extract_from_wikitext(course_name: str, wiki_title: str, wikitext: str) -> dict:
    """Extract metadata fields from a verified Wikipedia page."""
    result = {
        "course_name": course_name,
        "wiki_title": wiki_title,
        "wiki_status": "found",
        "country": None,
        "region": None,
        "yardage": None,
        "par": None,
        "designed_year": None,
        "designer": None,
        "course_types": [],
        "coastal": None,
    }
    
    yardage_raw = extract_field(
        wikitext, 
        "length1", "length2", "length", 
        "yards", "course_length", "total_length"
    )
    result["yardage"] = parse_yardage(yardage_raw) if yardage_raw else None

    par_raw = extract_field(
        wikitext, 
        "par1", "par2", "par", "course_par"
    )
    result["par"] = parse_par(par_raw) if par_raw else None

    designer_raw = extract_field(wikitext, "designer", "architect", "course_designer")
    result["designer"] = designer_raw if designer_raw else None
    
    opened_raw = extract_field(wikitext, "established", "opened", "year_built", "year_opened", "founded")
    result["designed_year"] = parse_year(opened_raw) if opened_raw else None
    
    country_raw = extract_field(wikitext, "country", "location")
    result["country"] = parse_country(country_raw) if country_raw else None
    if not result["country"]:
        for c in COUNTRY_REGIONS.keys():
            if c.lower() in wikitext.lower()[:3000]:
                result["country"] = c
                break
    result["region"] = COUNTRY_REGIONS.get(result["country"])
    
    # Use the strict lead-paragraph detection for type
    result["course_types"] = identify_course_type(wikitext)
    
    # Coastal: only true if links OR mentioned in the lead paragraph
    lead = _extract_first_paragraph(wikitext).lower()
    coastal_in_lead = any(kw in lead for kw in [
        "coastal", "seaside", "links course", "on the coast",
        "overlooks the", "overlooking the", "beach", "ocean shore",
    ])
    result["coastal"] = coastal_in_lead or "links" in result["course_types"]
    
    return result

def load_existing_metadata() -> dict:
    """Load already-scraped metadata."""
    if META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rescrape all courses")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    # Get list of courses from your data
    rounds_path = RAW_DIR / "all-rounds.parquet"
    if not rounds_path.exists():
        sys.exit(f"ERROR: {rounds_path} not found. Run the data fetch first.")
    
    df = pd.read_parquet(rounds_path)
    courses = sorted(df["course_name"].unique())
    print(f"Found {len(courses)} unique courses")
    
    metadata = load_existing_metadata()
    
    if args.limit:
        courses = courses[:args.limit]
    
    scraped = 0
    found = 0
    skipped = 0
    
    for i, course in enumerate(courses, 1):
        if course in metadata and not args.force:
            skipped += 1
            continue
        
        print(f"\n[{i}/{len(courses)}] {course}")
        result = scrape_course(course)
        
        if result["wiki_status"] == "found":
            print(f"  ✓ {result['wiki_title']}")
            print(f"    Country: {result['country']} / Region: {result['region']}")
            print(f"    Yardage: {result['yardage']} / Par: {result['par']}")
            print(f"    Types: {result['course_types']}")
            print(f"    Coastal: {result['coastal']}")
            found += 1
        else:
            print(f"  ✗ Not found")
        
        metadata[course] = result
        scraped += 1
        
        # Save progress every 10 courses
        if i % 10 == 0:
            META_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True))
        
        time.sleep(0.5)  # be polite to Wikipedia
    
    META_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    
    print(f"\nDone.")
    print(f"  Scraped: {scraped}")
    print(f"  Found: {found}")
    print(f"  Skipped (already had): {skipped}")
    print(f"  Saved to {META_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()