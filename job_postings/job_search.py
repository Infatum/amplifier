from jobspy import scrape_jobs
from datetime import datetime, timezone
from typing import Sequence
import xml.etree.ElementTree as ET
import urllib.request
import sqlite3
import json
import pandas as pd
import html
import re

JOBS_DB = "job_postings/jobs.db"
DOU_FEED = "https://jobs.dou.ua/vacancies/feeds/"
REMOTEOK_API = "https://remoteok.com/api"
REMOTIVE_API = "https://remotive.com/api/remote-jobs"
HIMALAYAS_API = "https://himalayas.app/jobs/api"
NOMADS_API = "https://www.workingnomads.com/api/exposed_jobs/"
WWR_FEED = "https://weworkremotely.com/remote-jobs.rss"
ASHBY_BOARD = "https://api.ashbyhq.com/posting-api/job-board/{company}"
DOU_TITLE = re.compile(r"^(?P<title>.+?)\s+в\s+(?P<rest>.+)$") 


def get_timestamp() -> str:
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
            jobs["scraped_at"] = get_timestamp()
            frames.append(jobs)

    if "dou" in sources and category:
        frames.append(load_dou_jobs(category, remote_only))

    if not frames:
        return pd.DataFrame()

    jobs = pd.concat(frames, ignore_index=True)

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

    scraped_at = get_timestamp()

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
            "id": link.split("?")[0].rstrip("/").split("/")[-1],
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


def save_jobs(jobs: pd.DataFrame, db_path: str = JOBS_DB, table: str = "jobs") -> int:
    if jobs.empty:
        return 0

    rows = jobs.copy()
    for column in rows.columns:
        if rows[column].map(lambda v: isinstance(v, (list, tuple, set, dict))).any():
            rows[column] = rows[column].map(lambda v: ", ".join(map(str, v))
                                            if isinstance(v, (list, tuple, set)) else v)
    rows = rows.astype(object).where(pd.notna(rows), None)
    connection = sqlite3.connect(db_path)
    
    try:
        columns = list(rows.columns)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table} ("
            + ", ".join(f'"{c}"' for c in columns)
            + ', PRIMARY KEY ("site", "id"))'
        )
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column in columns:
            if column not in existing:
                connection.execute(f'ALTER TABLE {table} ADD COLUMN "{column}"')

        placeholders = ", ".join("?" * len(columns))
        connection.executemany(
            f"INSERT OR REPLACE INTO {table} ("
            + ", ".join(f'"{c}"' for c in columns)
            + f") VALUES ({placeholders})",
            rows.itertuples(index=False, name=None),
        )
        connection.commit()
        return len(rows)
    finally:
        connection.close()


# --------------------------------------------------------------------------
# Remote-only boards.
#
# Every posting on these is remote by definition, so is_remote is hardcoded
# True rather than read from a field the source does not have. Columns match
# load_jobs() output so every source concatenates into one table.
# --------------------------------------------------------------------------

BOARD_COLUMNS = (
    "site", "id", "job_url", "title", "company", "location", "is_remote",
    "min_amount", "max_amount", "currency", "interval", "job_type",
    "date_posted", "description", "scraped_at",
)


def fetch_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(request, timeout=25).read().decode("utf-8", "replace"))


def fetch_xml(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return ET.fromstring(urllib.request.urlopen(request, timeout=25).read())


def board_frame(rows: list) -> pd.DataFrame:
    """Same columns for every board, missing ones as None."""
    return pd.DataFrame(rows, columns=list(BOARD_COLUMNS))


def load_remoteok_jobs() -> pd.DataFrame:
    scraped_at = get_timestamp()
    # Element 0 is a legal notice, not a vacancy.
    return board_frame([{
        "site": "remoteok", "id": str(job.get("id", "")), "job_url": job.get("url"),
        "title": job.get("position"), "company": job.get("company"),
        "location": job.get("location"), "is_remote": True,
        # RemoteOK writes 0 when no salary is given, not null -- keeping the
        # zero would make "has a salary" true for 80 of 99 postings.
        "min_amount": job.get("salary_min") or None,
        "max_amount": job.get("salary_max") or None,
        "currency": "USD" if job.get("salary_min") else None,
        "interval": "yearly" if job.get("salary_min") else None,
        "job_type": None, "date_posted": job.get("date"),
        "description": job.get("description"), "scraped_at": scraped_at,
    } for job in fetch_json(REMOTEOK_API)[1:]])


def load_remotive_jobs(search: str | None = None) -> pd.DataFrame:
    scraped_at = get_timestamp()
    url = REMOTIVE_API + (f"?search={urllib.parse.quote(search)}" if search else "")
    return board_frame([{
        "site": "remotive", "id": str(job.get("id", "")), "job_url": job.get("url"),
        "title": job.get("title"), "company": job.get("company_name"),
        "location": job.get("candidate_required_location"), "is_remote": True,
        "min_amount": None, "max_amount": None, "currency": None, "interval": None,
        "job_type": job.get("job_type"), "date_posted": job.get("publication_date"),
        "description": job.get("description"), "scraped_at": scraped_at,
    } for job in fetch_json(url).get("jobs", [])])


def load_himalayas_jobs(wanted: int = 100) -> pd.DataFrame:
    """Himalayas caps a page at 20 whatever `limit` says, so follow nextCursor."""
    scraped_at = get_timestamp()
    jobs, cursor = [], None
    while len(jobs) < wanted:
        url = f"{HIMALAYAS_API}?limit=20"
        if cursor:
            url += f"&cursor={urllib.parse.quote(str(cursor))}"
        payload = fetch_json(url)
        page = payload.get("jobs", [])
        if not page:
            break
        jobs.extend(page)
        cursor = payload.get("nextCursor")
        if not cursor:
            break

    rows = []
    for job in jobs[:wanted]:
        places = job.get("locationRestrictions") or []
        rows.append({
            "site": "himalayas", "id": str(job.get("guid", "")),
            "job_url": job.get("applicationLink"), "title": job.get("title"),
            "company": job.get("companyName"),
            "location": ", ".join(places) if isinstance(places, list) else places,
            "is_remote": True,
            "min_amount": job.get("minSalary"), "max_amount": job.get("maxSalary"),
            "currency": job.get("currency"), "interval": job.get("salaryPeriod"),
            "job_type": job.get("employmentType"), "date_posted": job.get("pubDate"),
            "description": job.get("description"), "scraped_at": scraped_at,
        })
    return board_frame(rows)


def load_nomads_jobs() -> pd.DataFrame:
    scraped_at = get_timestamp()
    rows = []
    for job in fetch_json(NOMADS_API):
        url = job.get("url") or ""
        rows.append({
            "site": "workingnomads",
            "id": url.split("?")[0].rstrip("/").split("/")[-1],
            "job_url": url, "title": job.get("title"), "company": job.get("company_name"),
            "location": job.get("location"), "is_remote": True,
            "min_amount": None, "max_amount": None, "currency": None, "interval": None,
            "job_type": None, "date_posted": job.get("pub_date"),
            "description": job.get("description"), "scraped_at": scraped_at,
        })
    return board_frame(rows)


def load_wwr_jobs() -> pd.DataFrame:
    """We Work Remotely RSS. Titles read "Company: Role"."""
    scraped_at = get_timestamp()
    rows = []
    for item in fetch_xml(WWR_FEED).findall(".//item"):
        get = lambda tag: (item.findtext(tag) or "").strip()
        raw = html.unescape(get("title"))
        company, _, title = raw.partition(":")
        link = get("link")
        rows.append({
            "site": "weworkremotely",
            "id": link.split("?")[0].rstrip("/").split("/")[-1],
            "job_url": link, "title": (title or raw).strip(), "company": company.strip(),
            "location": ", ".join(p for p in (get("region"), get("country")) if p),
            "is_remote": True,
            "min_amount": None, "max_amount": None, "currency": None, "interval": None,
            "job_type": get("type") or None, "date_posted": get("pubDate"),
            "description": get("description"), "scraped_at": scraped_at,
        })
    return board_frame(rows)


REMOTE_BOARDS = {
    "remoteok": load_remoteok_jobs,
    "remotive": load_remotive_jobs,
    "himalayas": load_himalayas_jobs,
    "workingnomads": load_nomads_jobs,
    "weworkremotely": load_wwr_jobs,
}


def load_ashby_jobs(companies, remote_only: bool = True) -> pd.DataFrame:
    """Postings straight from a company's own Ashby board.

    Unlike the aggregators this is targeted: you pass the companies you care
    about. Ashby reports isRemote itself, so the remote filter is exact here
    rather than a guess -- no description sniffing needed.

    A company not on Ashby returns no jobs instead of raising, so a wrong
    slug is silent. Check the count when you add one.
    """
    scraped_at = get_timestamp()
    rows = []
    for company in companies:
        try:
            payload = fetch_json(ASHBY_BOARD.format(company=company))
        except Exception:
            continue
        for job in payload.get("jobs", []):
            if remote_only and not job.get("isRemote"):
                continue
            rows.append({
                "site": f"ashby:{company}", "id": str(job.get("id", "")),
                "job_url": job.get("jobUrl") or job.get("applyUrl"),
                "title": job.get("title"), "company": company,
                "location": job.get("location"), "is_remote": bool(job.get("isRemote")),
                "min_amount": None, "max_amount": None, "currency": None, "interval": None,
                "job_type": job.get("employmentType"), "date_posted": job.get("publishedAt"),
                "description": job.get("descriptionPlain"), "scraped_at": scraped_at,
            })
    return board_frame(rows)
