"""
scrape_course_metadata_agent.py
-------------------------------
Extracts golf course metadata using Claude with web search.

Workflow:
  For each course → Claude searches the web → returns structured JSON → saved.

Usage:
    python scrape_course_metadata_agent.py
    python scrape_course_metadata_agent.py --force      # rescrape all
    python scrape_course_metadata_agent.py --limit 10   # test on a few
    python scrape_course_metadata_agent.py --courses "Royal Birkdale" "Pebble Beach Golf Links"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

# ─── Setup ─────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
META_PATH = DATA_DIR / "course_metadata.json"
META_PATH.parent.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / "analysis" / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    sys.exit("ERROR: ANTHROPIC_API_KEY not set in analysis/.env")

client = Anthropic(api_key=ANTHROPIC_API_KEY)


# ─── Extraction prompt ─────────────────────────────────────────────────

EXTRACTION_PROMPT = """Find authoritative information about the golf course named: "{course_name}"

Search the web for the most reliable source — the course's official website, Wikipedia, top100golfcourses.com, golfdigest.com, golfclubatlas.com, or other reputable golf publications.

Be careful: 
- Don't confuse the course with a tournament that's played there (e.g. "Bay Hill" the course ≠ "Arnold Palmer Invitational" the tournament)
- Don't confuse the course with its designer
- For multi-course resorts (Pinehurst, Sea Island, etc.), find the specific course mentioned
- For courses with parentheticals like "(South)" or "(Champion)" — that's the specific course at a multi-course facility

Extract these fields and return ONLY a JSON object wrapped in ```json``` fences:

- "country": Full country name (e.g. "United States", "England", "Scotland", "Japan"). Required.
- "region": "USA" | "UK" | "Europe" | "Asia/Pacific" | "Middle East" | "Africa" | "Other". UK = England/Scotland/Wales/Ireland/Northern Ireland.
- "yardage": Total course length in yards as integer. Typical range 6500-7800.
- "par": Course par as integer. Almost always 70, 71, or 72.
- "designed_year": Year course originally opened, as 4-digit integer.
- "designer": Original architect's full name as string (e.g. "Donald Ross", "Pete Dye", "Alister MacKenzie"). Don't include renovation architects.
- "course_type": Pick ONE most accurate: "links" | "parkland" | "heathland" | "desert" | "stadium" | "mountain" | "coastal" | "other"
  - "links": coastal Scottish/Irish/English-style with fescue grass, no trees, natural dunes
  - "parkland": typical wooded inland American/European course (most common)
  - "heathland": inland heath terrain (mostly UK)
  - "desert": arid southwest US, Middle East
  - "stadium": purpose-built tournament course with mounded spectator areas (most TPC courses)
  - "mountain": significant elevation changes, mountain setting
  - "coastal": on or near the coast but NOT a true links
- "coastal": true if literally on/near the coast, false otherwise
- "tree_lined": true if tree-lined/wooded, false if open/treeless, null if unclear
- "elevation_m": Elevation above sea level in metres as integer, or null

Be conservative — return null only when no source provides the data. Don't guess.

Return your response in this exact format:

```json
{{
  "country": "...",
  "region": "...",
  "yardage": 0,
  "par": 0,
  "designed_year": 0,
  "designer": "...",
  "course_type": "...",
  "coastal": false,
  "tree_lined": false,
  "elevation_m": 0
}}
```
"""


def extract_with_agent(course_name: str) -> Optional[dict]:
    prompt = EXTRACTION_PROMPT.format(course_name=course_name)
    
    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 3,  # reduced from 5
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            
            # Get the text response
            all_text = "\n".join(
                block.text for block in message.content 
                if hasattr(block, 'text')
            )
            
            json_match = re.search(r"```(?:json)?\s*(\{[^`]+?\})\s*```", all_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", all_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            print(f"    ⚠ No JSON found")
            return None
        
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                wait = 30 * (attempt + 1)
                print(f"    ⏱ Rate limit — waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
                continue
            print(f"    ⚠ {type(e).__name__}: {e}")
            return None
    
    print(f"    ⚠ Gave up after 3 retries")
    return None


# ─── Main loop ─────────────────────────────────────────────────────────

def load_existing_metadata() -> dict:
    if META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return {}


def scrape_course(course_name: str) -> dict:
    """Run agent and package result."""
    result = {
        "course_name": course_name,
        "status": "failed",
        "source": "web_search",
    }
    
    extracted = extract_with_agent(course_name)
    if not extracted:
        return result
    
    return {
        "course_name": course_name,
        "status": "found",
        "source": "web_search",
        **extracted,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rescrape all courses")
    parser.add_argument("--limit", type=int, default=None, help="Limit number to process")
    parser.add_argument("--courses", nargs="+", default=None, help="Specific courses only")
    args = parser.parse_args()
    
    # Determine which courses to process
    if args.courses:
        courses = args.courses
        print(f"Processing {len(courses)} specified courses")
    else:
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
            if existing.get("status") == "found":
                skipped += 1
                continue
        
        print(f"\n[{i}/{len(courses)}] {course}")
        result = scrape_course(course)
        
        if result["status"] == "found":
            print(f"    Country: {result.get('country')} ({result.get('region')})")
            print(f"    Type: {result.get('course_type')} (coastal: {result.get('coastal')})")
            print(f"    Yardage: {result.get('yardage')} / Par: {result.get('par')}")
            print(f"    Designer: {result.get('designer')} ({result.get('designed_year')})")
            found += 1
        else:
            print(f"  ✗ Failed")
            failed += 1
        
        metadata[course] = result
        
        # Save every 5 courses (in case of crash)
        if i % 5 == 0:
            META_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True))
        
        # Light delay between API calls
        time.sleep(1.0)
    
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