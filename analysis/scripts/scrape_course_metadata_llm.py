"""
scrape_course_metadata_llm.py
------------------------------
Extracts golf course metadata from Wikipedia using Claude as the parser.

Workflow:
  1. Search Wikipedia for the course
  2. Fetch the page wikitext
  3. Send to Claude with a structured prompt
  4. Save clean JSON to data/course_metadata.json

Usage:
    python scrape_course_metadata_llm.py              # process missing courses
    python scrape_course_metadata_llm.py --force      # rescrape all
    python scrape_course_metadata_llm.py --limit 10   # test on small batch
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import deque
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from anthropic import Anthropic
from dotenv import load_dotenv

# ─── Setup ─────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
META_PATH = DATA_DIR / "course_metadata.json"
META_PATH.parent.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / "analysis" / ".env")

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "CaddieDesk/1.0 (caddiedesk.com)"}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    sys.exit("ERROR: ANTHROPIC_API_KEY not set in analysis/.env")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Wikipedia rate limiting
_request_times = deque()
_WIKI_RATE_LIMIT = 20
_WIKI_WINDOW = 60


def _rate_limited_get(url, **kwargs):
    now = time.time()
    while _request_times and now - _request_times[0] > _WIKI_WINDOW:
        _request_times.popleft()
    if len(_request_times) >= _WIKI_RATE_LIMIT:
        wait = _WIKI_WINDOW - (now - _request_times[0]) + 0.5
        print(f"    ⏱ Wikipedia rate limit pause: {wait:.1f}s")
        time.sleep(wait)
    _request_times.append(time.time())
    response = requests.get(url, **kwargs)
    if response.status_code == 429:
        print(f"    ⏱ 429 — backing off 60s")
        time.sleep(60)
    return response


# ─── Manual overrides (for ambiguous course names) ─────────────────────

MANUAL_OVERRIDES = {
    # ─── TPC venues ─────────────────────────────────────
    "TPC River Highlands": "TPC_River_Highlands",
    "TPC Southwind": "TPC_Southwind",
    "TPC Deere Run": "TPC_Deere_Run",
    "TPC Scottsdale": "TPC_Scottsdale",
    "TPC Sawgrass": "TPC_at_Sawgrass",
    "TPC Boston": "TPC_Boston",
    "TPC Summerlin": "TPC_Summerlin",
    "TPC Potomac at Avenel Farm": "TPC_Potomac_at_Avenel_Farm",
    "TPC Twin Cities": "TPC_Twin_Cities",
    "TPC San Antonio (Oaks)": "TPC_San_Antonio",
    "TPC Craig Ranch": "TPC_Craig_Ranch",
    "TPC Louisiana": "TPC_Louisiana",
    "TPC Harding Park": "Harding_Park_Golf_Course",
    "TPC Toronto at Osprey Valley (North Course)": "Osprey_Valley",
    "TPC Four Seasons Resort": "TPC_Four_Seasons_Resort_and_Club_Las_Colinas",
    
    # ─── The Open Championship rota ─────────────────────
    "Royal Liverpool": "Royal_Liverpool_Golf_Club",
    "Royal Birkdale": "Royal_Birkdale_Golf_Club",
    "Royal Troon": "Royal_Troon_Golf_Club",
    "Royal Portrush Golf Club": "Royal_Portrush_Golf_Club",
    "Carnoustie Golf Links": "Carnoustie_Golf_Links",
    "Muirfield": "Muirfield",
    "Royal Lytham & St Annes": "Royal_Lytham_%26_St_Annes_Golf_Club",
    "Royal St George's": "Royal_St_George's_Golf_Club",
    "Old Course at St Andrews": "Old_Course_at_St_Andrews",
    
    # ─── US Open venues ─────────────────────────────────
    "Pebble Beach Golf Links": "Pebble_Beach_Golf_Links",
    "Spyglass Hill Golf Course": "Spyglass_Hill_Golf_Course",
    "Augusta National Golf Club": "Augusta_National_Golf_Club",
    "Pinehurst Resort & Country Club (Course No. 2)": "Pinehurst_Resort",
    "Bethpage Black": "Bethpage_State_Park",
    "Winged Foot GC": "Winged_Foot_Golf_Club",
    "Oakmont Country Club": "Oakmont_Country_Club",
    "Shinnecock Hills GC": "Shinnecock_Hills_Golf_Club",
    "Merion GC (East)": "Merion_Golf_Club",
    "Olympia Fields Country Club (North)": "Olympia_Fields_Country_Club",
    "Whistling Straits": "Whistling_Straits",
    "Erin Hills": "Erin_Hills",
    "Chambers Bay": "Chambers_Bay",
    "Torrey Pines Golf Course (South Course)": "Torrey_Pines_Golf_Course",
    "Torrey Pines Golf Course (North Course)": "Torrey_Pines_Golf_Course",
    "Harding Park GC": "Harding_Park_Golf_Course",
    
    # ─── PGA Championship venues ────────────────────────
    "Quail Hollow Club": "Quail_Hollow_Club",
    "Bellerive Country Club": "Bellerive_Country_Club",
    "Baltusrol Golf Club": "Baltusrol_Golf_Club",
    "Hazeltine National GC": "Hazeltine_National_Golf_Club",
    "Crooked Stick Golf Club": "Crooked_Stick_Golf_Club",
    "Medinah Country Club": "Medinah_Country_Club",
    "Valhalla Golf Club": "Valhalla_Golf_Club",
    "Southern Hills Country Club": "Southern_Hills_Country_Club",
    "Ocean Course at Kiawah Island": "Kiawah_Island_Golf_Resort",
    "Trump National Doral": "Trump_National_Doral_Miami",
    "Aronimink Golf Club": "Aronimink_Golf_Club",
    
    # ─── PGA Tour regular venues ────────────────────────
    "Bay Hill Club & Lodge": "Bay_Hill_Club_and_Lodge",
    "East Lake Golf Club": "East_Lake_Golf_Club",
    "Muirfield Village Golf Club": "Muirfield_Village_Golf_Club",
    "Firestone CC (South)": "Firestone_Country_Club",
    "Colonial CC": "Colonial_Country_Club_(Fort_Worth,_Texas)",
    "Colonial Country Club": "Colonial_Country_Club_(Fort_Worth,_Texas)",
    "Waialae Country Club": "Waialae_Country_Club",
    "Plantation Course at Kapalua": "Kapalua_Resort",
    "Innisbrook Resort (Copperhead)": "Innisbrook_Resort_and_Golf_Club",
    "Sedgefield Country Club": "Sedgefield_Country_Club",
    "PGA National (Champion)": "PGA_National_Resort_%26_Spa",
    "Sea Island Golf Club (Seaside Course)": "Sea_Island_Resort",
    "Sea Island Golf Club (Plantation Course)": "Sea_Island_Resort",
    "Detroit Golf Club": "Detroit_Golf_Club",
    "Trinity Forest Golf Club": "Trinity_Forest_Golf_Club",
    "Liberty National Golf Club": "Liberty_National_Golf_Club",
    "Memorial Park Golf Course": "Memorial_Park_Golf_Course",
    "Sherwood Country Club": "Sherwood_Country_Club",
    "Harbour Town Golf Links": "Harbour_Town_Golf_Links",
    "Riviera Country Club": "Riviera_Country_Club",
    "Castle Pines Golf Club": "Castle_Pines_Golf_Club",
    "Cherry Hills CC": "Cherry_Hills_Country_Club",
    "Cherry Hills Country Club": "Cherry_Hills_Country_Club",
    "Caves Valley Golf Club": "Caves_Valley_Golf_Club",
    "Conway Farms GC": "Conway_Farms_Golf_Club",
    "Cog Hill G&CC": "Cog_Hill_Golf_%26_Country_Club",
    "Plainfield Country Club": "Plainfield_Country_Club",
    "Eagle Point Golf Club": "Eagle_Point_Golf_Club",
    "Congaree Golf Club": "Congaree_Golf_Club",
    "Congressional CC (Blue)": "Congressional_Country_Club",
    "Glen Oaks Club": "Glen_Oaks_Club",
    "Ridgewood CC": "Ridgewood_Country_Club",
    "Wilmington Country Club": "Wilmington_Country_Club",
    "Westchester CC": "Westchester_Country_Club",
    "Oak Hill Country Club": "Oak_Hill_Country_Club",
    "Shadow Creek Golf Course": "Shadow_Creek_Golf_Course",
    "Maridoe Golf Club": "Maridoe_Golf_Club",
    "The Country Club": "The_Country_Club",
    "The Los Angeles Country Club (North Course)": "Los_Angeles_Country_Club",
    "The Philadelphia Cricket Club (Wissahickon Course)": "Philadelphia_Cricket_Club",
    "The Concession Golf Club": "The_Concession_Golf_Club",
    "The Summit Club": "The_Summit_Club_at_Cordillera",  # might be wrong, double-check
    "Robert Trent Jones Golf Club": "Robert_Trent_Jones_Golf_Club",
    "Las Vegas Country Club": "Las_Vegas_Country_Club",
    "Bolingbrook Golf Club": "Bolingbrook_Golf_Club",
    "La Quinta Country Club": "La_Quinta_Country_Club",
    "The Old White TPC": "Greenbrier_Resort",
    "RTJ Trail (Grand National)": "Robert_Trent_Jones_Golf_Trail",
    
    # ─── DP World Tour / Europe ─────────────────────────
    "Wentworth Club (West)": "Wentworth_Club",
    "The Renaissance Club": "The_Renaissance_Club",
    "Le Golf National": "Le_Golf_National",
    "Valderrama Golf Club": "Valderrama_Golf_Club",
    "Mount Juliet": "Mount_Juliet_Estate",
    "JCB Golf and Country Club": "JCB_Golf_and_Country_Club",
    "The Grove": "The_Grove,_Hertfordshire",
    
    # ─── Korn Ferry / smaller venues ────────────────────
    "Bolingbrook Golf Club": "Bolingbrook_Golf_Club",
    "Pete Dye Stadium Course": "Pete_Dye_Course_at_French_Lick_Resort",
    "Forest Oaks CC": "Forest_Oaks_Country_Club",
    
    # ─── International venues ───────────────────────────
    "Albany Golf Club": "Albany_(resort)",
    "Hong Kong Golf Club": "Hong_Kong_Golf_Club",
    "Sentosa Golf Club": "Sentosa_Golf_Club",
    "Kasumigaseki Country Club": "Kasumigaseki_Country_Club",
    "ACCORDIA GOLF Narashino Country Club": "Accordia_Golf_Narashino_Country_Club",
    "Royal Greens Golf & Country Club": "Royal_Greens_Golf_and_Country_Club",
    "Riyadh Golf Club": "Riyadh_Golf_Club",
    "Vidanta Vallarta": "Vidanta_Nuevo_Vallarta",
    "El Camaleon Golf Club": "El_Camaleón_Golf_Club",
    "Club de Golf Chapultepec": "Club_de_Golf_Chapultepec",
    "The Grange Golf Club": "The_Grange_Golf_Club",  # might be Adelaide
    "Black Desert Resort": "Black_Desert_Resort",
    "The Club at Steyn City": "Steyn_City",
    
    # ─── Canadian ───────────────────────────────────────
    "Angus Glen Golf Club": "Angus_Glen_Golf_Club",
    "Glen Abbey Golf Club": "Glen_Abbey_Golf_Club",
    "Hamilton Golf & Country Club": "Hamilton_Golf_and_Country_Club",
    "St. George's G&CC": "St._George's_Golf_and_Country_Club",
    "Oakdale Golf & Country Club": "Oakdale_Golf_and_Country_Club",
    "Shaughnessy G&CC": "Shaughnessy_Golf_and_Country_Club",
    "Royal Montreal GC (Blue)": "Royal_Montreal_Golf_Club",
    
    # ─── Likely no Wikipedia page (web search will catch) ─
    # Annandale GC, Country Club of Jackson, Country Club at Mirasol,
    # GC of Houston, Hurstbourne, Keene Trace, LaCantera (Resort),
    # Maridoe, Montreux, Nicklaus Tournament Course, Tahoe Mountain Club,
    # Trump National Washington, The Club at Chatham Hills
}


# ─── Wikipedia fetching ────────────────────────────────────────────────

def search_wiki(query: str) -> list[str]:
    """Search Wikipedia, return top 5 candidate page titles."""
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": 5,
    }
    for attempt in range(3):
        try:
            r = _rate_limited_get(WIKI_API, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return [h["title"] for h in r.json().get("query", {}).get("search", [])]
        except (requests.RequestException, ValueError) as e:
            print(f"    Search retry {attempt+1}/3: {e}")
            time.sleep(15)
    return []


def get_wiki_page(title: str) -> Optional[str]:
    """Fetch the wikitext of a Wikipedia page. Returns the raw text or None."""
    params = {
        "action": "parse",
        "format": "json",
        "page": title,
        "prop": "wikitext",
    }
    for attempt in range(3):
        try:
            r = _rate_limited_get(WIKI_API, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
            return data.get("parse", {}).get("wikitext", {}).get("*")
        except (requests.RequestException, ValueError) as e:
            print(f"    Page retry {attempt+1}/3 for '{title}': {e}")
            time.sleep(15)
    return None


def find_wikipedia_page(course_name: str) -> tuple[Optional[str], Optional[str]]:
    """Find the best Wikipedia page for a course. Returns (title, wikitext)."""
    
    # Check manual override first
    if course_name in MANUAL_OVERRIDES:
        title = MANUAL_OVERRIDES[course_name]
        wikitext = get_wiki_page(title)
        if wikitext:
            return title, wikitext
    
    # Build search variants
    variants = [course_name]
    
    # Expand common abbreviations
    expansions = [
        (" GC", " Golf Club"),
        (" CC", " Country Club"),
        (" G&CC", " Golf and Country Club"),
        (" GL", " Golf Links"),
    ]
    for abbr, full in expansions:
        if abbr in course_name:
            variants.append(course_name.replace(abbr, full))
    
    # Strip parenthetical disambiguators like "(South)"
    no_paren = re.sub(r"\s*\([^)]+\)\s*", " ", course_name).strip()
    if no_paren != course_name:
        variants.append(no_paren)
        for abbr, full in expansions:
            if abbr in no_paren:
                variants.append(no_paren.replace(abbr, full))
    
    # Deduplicate
    variants = list(dict.fromkeys(variants))
    
    # Try each variant; take the first candidate that returns wikitext
    for variant in variants:
        candidates = search_wiki(variant)
        for cand in candidates[:2]:  # only top 2 per variant to limit cost
            wikitext = get_wiki_page(cand)
            if wikitext and _likely_golf_page(wikitext, cand):
                return cand, wikitext
    
    return None, None


def _likely_golf_page(wikitext: str, title: str) -> bool:
    title_lower = title.lower()
    text_lower = wikitext[:5000].lower()
    
    # Reject person pages
    person_indicators = [
        "infobox person",
        "infobox golfer",
        "infobox architect",
        r"\(born ",
        r"\(died ",
    ]
    for indicator in person_indicators:
        if re.search(indicator, text_lower):
            return False
    
    # Reject tournament/event pages by infobox
    tournament_infoboxes = [
        "infobox golf tournament",
        "infobox golf event",
        "infobox sporting event",
        "infobox annual event",
    ]
    if any(t in text_lower for t in tournament_infoboxes):
        return False
    
    # Reject by title keywords
    tournament_words = [
        "championship", "open", "invitational", "tournament", "cup", 
        "playoff", "challenge", "classic", "trophy", "series",
    ]
    if any(w in title_lower for w in tournament_words):
        if not any(w in title_lower for w in ["golf club", "country club", "course"]):
            return False
    
    # Must have golf-course infobox indicator
    return any(t in text_lower for t in [
        "infobox golf facility",
        "infobox golf course",
        "infobox golf club",
    ])


# ─── Claude extraction ─────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are extracting structured data about a golf course from a Wikipedia article.

Below is the wikitext for a Wikipedia page. Extract the following fields and return ONLY a JSON object, no other text.

Fields to extract:
- "country": The country (e.g. "United States", "England", "Scotland", "Japan"). Use full country names.
- "region": "USA" | "UK" | "Europe" | "Asia/Pacific" | "Middle East" | "Africa" | "Other". UK includes England/Scotland/Wales/Ireland/Northern Ireland.
- "yardage": Total course length in yards as integer, or null if unclear. Look for course length, not individual hole yardages.
- "par": Course par as integer (typically 70, 71, or 72), or null.
- "designed_year": Year the course was originally opened/established, as 4-digit integer, or null.
- "designer": The original architect/designer's name as string, or null. Don't include renovation architects.
- "course_type": One of: "links" | "parkland" | "heathland" | "desert" | "stadium" | "mountain" | "coastal" | "other". Choose the SINGLE most accurate type from the lead description. "Links" courses are coastal Scottish/Irish/English style. "Parkland" is the typical American/wooded inland course. Only use "coastal" if explicitly described as coastal/seaside but NOT a true links course.
- "coastal": true if the course is on the coast or has significant coastal/oceanside character. Most links courses are coastal.
- "tree_lined": true if explicitly described as tree-lined or wooded, false if open/treeless, null if unclear.
- "elevation_m": Elevation above sea level in metres, integer, or null. Convert from feet if needed (1 ft = 0.3048 m).

Be conservative — return null for fields where you can't find clear evidence. Don't guess.

Return ONLY the JSON object, nothing else. No markdown fences, no preamble.

Wikipedia article:
"""


def extract_with_llm(wikitext: str, course_name: str) -> Optional[dict]:
    """Use Claude to extract structured metadata from wikitext."""
    
    # Truncate wikitext to a reasonable size (first ~12000 chars usually has the infobox + lead)
    truncated = wikitext[:12000]
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + truncated,
                }
            ],
        )
        response_text = message.content[0].text.strip()
        
        # Strip markdown fences if Claude wrapped it
        response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
        response_text = re.sub(r"\s*```$", "", response_text)
        
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"    ⚠ JSON parse error: {e}")
        print(f"    Response was: {response_text[:200]}")
        return None
    except Exception as e:
        print(f"    ⚠ LLM error: {e}")
        return None


# ─── Main scrape function ─────────────────────────────────────────────

def scrape_course(course_name: str) -> dict:
    """Find course metadata. Tries Wikipedia first, falls back to web search."""
    result = {
        "course_name": course_name,
        "wiki_title": None,
        "wiki_status": "not_found",
    }
    
    # Try Wikipedia first
    title, wikitext = find_wikipedia_page(course_name)
    if title and wikitext:
        print(f"  ✓ Wikipedia: {title}")
        extracted = extract_with_llm(wikitext, course_name)
        if extracted:
            return {
                "course_name": course_name,
                "wiki_title": title,
                "wiki_status": "found",
                "source": "wikipedia",
                **extracted,
            }
    
    # Fall back to web search
    print(f"  → Wikipedia not found, trying web search...")
    extracted = extract_with_web_search(course_name)
    if extracted:
        return {
            "course_name": course_name,
            "wiki_status": "found_via_web",
            "source": "web_search",
            **extracted,
        }
    
    return result


def extract_with_web_search(course_name: str) -> Optional[dict]:
    """Use Claude with web search to find course data."""
    
    prompt = f"""Find information about the golf course called "{course_name}".

Search the web to find authoritative information about this course. Look for the course's official website, golf course databases (top100golfcourses.com, golfdigest.com, golfclubatlas.com), or reputable golf magazines.

Extract the following and return ONLY a JSON object inside ```json code fences:

- "country": Full country name (e.g. "United States", "England", "Japan"), or null
- "region": "USA" | "UK" | "Europe" | "Asia/Pacific" | "Middle East" | "Africa" | "Other"
- "yardage": Total course yardage as integer (5500-7500 range typical), or null
- "par": Course par as integer (typically 70-72), or null  
- "designed_year": Year course opened, 4-digit integer, or null
- "designer": Original architect name, or null
- "course_type": "links" | "parkland" | "heathland" | "desert" | "stadium" | "mountain" | "coastal" | "other"
- "coastal": true if coastal/seaside, false otherwise
- "tree_lined": true if tree-lined/wooded, false if open
- "elevation_m": Elevation in metres, or null

Be conservative: null if uncertain. Wrap the JSON in ```json ... ``` fences.
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        
        # Collect ALL text blocks (there might be commentary + JSON)
        all_text = "\n".join(
            block.text for block in message.content 
            if hasattr(block, 'text')
        )
        
        # Find JSON in code fences
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", all_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Fall back to finding any JSON object in the response
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", all_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        print(f"    ⚠ No JSON found in web search response")
        return None
    
    except json.JSONDecodeError as e:
        print(f"    ⚠ Web search JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"    ⚠ Web search error: {type(e).__name__}: {e}")
        return None

# ─── Main ──────────────────────────────────────────────────────────────

def load_existing_metadata() -> dict:
    if META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rescrape all courses")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of courses to process")
    args = parser.parse_args()
    
    rounds_path = RAW_DIR / "all-rounds.parquet"
    if not rounds_path.exists():
        sys.exit(f"ERROR: {rounds_path} not found.")
    
    df = pd.read_parquet(rounds_path)
    courses = sorted(df["course_name"].unique())
    print(f"Found {len(courses)} unique courses")
    
    metadata = load_existing_metadata()
    
    if args.limit:
        courses = courses[:args.limit]
    
    found = 0
    failed = 0
    skipped = 0
    
    for i, course in enumerate(courses, 1):
        if course in metadata and not args.force:
            existing = metadata[course]
            if existing.get("wiki_status") == "found":
                skipped += 1
                continue
        
        print(f"\n[{i}/{len(courses)}] {course}")
        result = scrape_course(course)
        
        if result["wiki_status"] in ("found", "found_via_web"):
            print(f"    Country: {result.get('country')} / Type: {result.get('course_type')}")
            print(f"    Yardage: {result.get('yardage')} / Par: {result.get('par')}")
            print(f"    Coastal: {result.get('coastal')} / Year: {result.get('designed_year')}")
            print(f"    Source: {result.get('source')}")
            found += 1
        else:
            print(f"  ✗ {result['wiki_status']}")
            failed += 1
        
        metadata[course] = result
        
        # Save every 5 courses
        if i % 5 == 0:
            META_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True))
        
        time.sleep(0.5)
    
    META_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    
    print(f"\n{'='*50}")
    print(f"Done.")
    print(f"  Found: {found}")
    print(f"  Failed: {failed}")
    print(f"  Skipped (already had): {skipped}")
    print(f"  Total in metadata: {len(metadata)}")
    print(f"  Saved to {META_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()