from jobspy import scrape_jobs
from datetime import datetime, timezone
from typing import Sequence
import xml.etree.ElementTree as ET
import urllib.request
import pandas as pd
import html
import re

DOU_FEED = "https://jobs.dou.ua/vacancies/feeds/"
DOU_TITLE = re.compile(r"^(?P<title>.+?)\s+в\s+(?P<rest>.+)$") 


def run_timestamp() -> str:
    """UTC, ISO-8601. One value per run, not per row.

    Shared by every row of a batch so "what did the 09:00 run return" stays
    answerable, and sorts correctly as text once it lands in SQLite.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_jobs(
        loacation: str,
        country: str,
        title: str,
        category: str | None = None,
        sources: Sequence=("linkedin", "indeed"),
        results_wanted: int=100,
        hours_old: int=72,
        remote_only: bool | None = False,
        job_type: str = "fulltime"
):
    frames = []
    # "dou" is ours, not a jobspy board -- it must not reach scrape_jobs.
    boards = [source for source in sources if source != "dou"]

    if boards:
        jobs = scrape_jobs(
            site_name=boards,
            search_term=title,
            location=loacation,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed=country,
            is_remote=remote_only,
            job_type=job_type
        )
        if not jobs.empty:
            jobs["scraped_at"] = run_timestamp()
            frames.append(jobs)

    if "dou" in sources and category:
        frames.append(load_dou_jobs(category, remote_only))

    if not frames:
        return pd.DataFrame()

    jobs = pd.concat(frames, ignore_index=True)

    # Lenient on purpose: drop only what is known to be non-remote, keep NaN.
    # Boards disagree on how they fill is_remote, so a missing value means
    # "unknown", not "office".
    if remote_only and "is_remote" in jobs:
        jobs = jobs[jobs.is_remote != False]

    return jobs


def parse_dou_title(raw: str) -> dict:
    raw = html.unescape(raw).strip()
    matched = DOU_TITLE.match(raw)
    if not matched:
        return {"title": raw, "company": "", "location": "", "is_remote": False, "min_amount": None}

    rest = matched.group("rest")
    parts = [p.strip() for p in rest.split(",")]
    company = parts[0]
    tail = parts[1:]

    is_remote = any("віддалено" in p.lower() for p in tail)
    salary = re.search(r"\$\s?(\d[\d\s]*)", rest)
    places = [p for p in tail if "віддалено" not in p.lower() and "$" not in p]

    return {
        "title": matched.group("title"),
        "company": company,
        "location": ", ".join(places),
        "is_remote": is_remote,
        "min_amount": int(salary.group(1).replace(" ", "")) if salary else None,
    }


def load_dou_jobs(category: str, remote_only: bool = True) -> pd.DataFrame:
    url = f"{DOU_FEED}?category={urllib.parse.quote(category)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(urllib.request.urlopen(request, timeout=20).read())

    scraped_at = run_timestamp()

    rows = []
    for item in root.findall(".//item"):
        get = lambda tag: (item.findtext(tag) or "").strip()
        parsed = parse_dou_title(get("title"))
        if remote_only and not parsed["is_remote"]:
            continue
        link = get("link")
        rows.append({
            "site": "dou",
            "scraped_at": scraped_at,
            "id": link.rstrip("/").split("/")[-1].split("?")[0],
            "job_url": link,
            "date_posted": get("pubDate"),
            "description": get("description"),
            "currency": "USD" if parsed["min_amount"] else None,
            "interval": "monthly" if parsed["min_amount"] else None,
            "max_amount": None,
            "job_type": None,
            **parsed,
        })
    return pd.DataFrame(rows)
