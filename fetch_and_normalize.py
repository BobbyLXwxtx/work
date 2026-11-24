"""Zero-dependency ETL pipeline for a $0.00 Canadian Federal Tender Feed.

Uses only the Python 3 standard library. Resolves the live CanadaBuys
Open Tender Notices CSV URL from the official Open Government Portal
(open.canada.ca) CKAN API, normalizes bilingual rows into clean English
records, computes daily diffs, validates schema invariants, and builds
both the paid CSV/JSON export and the public SEO preview storefront.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import io
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

CKAN_DATASET_URL = (
    "https://open.canada.ca/data/en/api/3/action/package_show"
    "?id=6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2"
)
MIN_EXPECTED_ROWS = 5


def fetch_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ZeroDollarCanadaBuysFeed/1.0 (+open-data)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8-sig", errors="replace")


def resolve_canadabuys_csv_url(ckan_payload: dict[str, Any]) -> str:
    resources = ckan_payload.get("result", {}).get("resources", [])
    for res in resources:
        name = str(res.get("name") or "").lower()
        fmt = str(res.get("format") or "").upper()
        if fmt == "CSV" and ("new tender" in name or "open tender" in name):
            return str(res["url"])
    for res in resources:
        if str(res.get("format") or "").upper() == "CSV" and res.get("url"):
            return str(res["url"])
    raise ValueError("Schema drift: no CSV resource found in CanadaBuys CKAN metadata")


def normalize_csv_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("Schema drift: empty CSV header")

    normalized: list[dict[str, str]] = []
    for row in reader:
        ref = str(
            row.get("referenceNumber-numeroReference")
            or row.get("solicitationNumber-numeroSollicitation")
            or ""
        ).strip()
        title = str(row.get("title-titre-eng") or "").strip()
        category = str(
            row.get("procurementCategory-categorieApprovisionnement") or "SRV"
        ).strip()
        status = str(
            row.get("tenderStatus-appelOffresStatut-eng") or "Open"
        ).strip()
        pub_date = str(row.get("publicationDate-datePublication") or "").strip()
        closing_date = str(
            row.get("tenderClosingDate-appelOffresDateCloture") or ""
        ).strip()
        notice_url = str(row.get("noticeURL-URLavis-eng") or "").strip()

        if not ref or not title:
            continue

        fingerprint = hashlib.sha256(
            f"{ref}|{title}|{status}|{closing_date}".encode("utf-8")
        ).hexdigest()[:16]

        normalized.append(
            {
                "reference_number": ref,
                "title": title,
                "category": category,
                "status": status,
                "publication_date": pub_date,
                "closing_date": closing_date,
                "notice_url": notice_url,
                "fingerprint": fingerprint,
            }
        )

    if len(normalized) < MIN_EXPECTED_ROWS:
        raise RuntimeError(
            f"Self-healing halt: expected >= {MIN_EXPECTED_ROWS} rows, got {len(normalized)}"
        )
    return normalized


def compute_diff(
    current: list[dict[str, str]], previous: list[dict[str, str]]
) -> dict[str, list[dict[str, str]]]:
    prev_map = {r["reference_number"]: r["fingerprint"] for r in previous}
    added = [r for r in current if r["reference_number"] not in prev_map]
    updated = [
        r
        for r in current
        if r["reference_number"] in prev_map
        and prev_map[r["reference_number"]] != r["fingerprint"]
    ]
    return {"added": added, "updated": updated}


def write_outputs(
    records: list[dict[str, str]],
    diff: dict[str, list[dict[str, str]]],
    dist_dir: Path,
    checkout_url: str,
) -> None:
    data_dir = dist_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "CanadaBuys Open Data (Open Government Licence - Canada)",
        "total_records": len(records),
        "added_today": len(diff["added"]),
        "updated_today": len(diff["updated"]),
        "records": records,
    }
    (data_dir / "latest.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8"
    )

    fieldnames = [
        "reference_number",
        "title",
        "category",
        "status",
        "publication_date",
        "closing_date",
        "notice_url",
        "fingerprint",
    ]
    with (data_dir / "latest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    preview_rows = "\n".join(
        f"<tr><td>{html.escape(r['publication_date'])}</td>"
        f"<td>{html.escape(r['category'])}</td>"
        f"<td>{html.escape(r['closing_date'])}</td>"
        f"<td><a href=\"{html.escape(r['notice_url'] or 'https://canadabuys.canada.ca/')}\" target=\"_blank\" rel=\"noopener\">{html.escape(r['title'])}</a></td></tr>"
        for r in records[:5]
    )
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CanadaBuys Federal Tender Feed</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 920px; margin: 48px auto; padding: 0 20px; color: #0f172a; line-height: 1.6; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  .meta {{ color: #475569; margin-bottom: 24px; }}
  .cta {{ display: inline-block; background: #2563eb; color: #fff; padding: 12px 20px; text-decoration: none; font-weight: 600; margin: 16px 0 32px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: 10px 12px 10px 0; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
  th {{ font-size: 0.85rem; color: #475569; border-bottom: 2px solid #0f172a; }}
</style>
</head>
<body>
  <h1>CanadaBuys Federal Tender Change Feed</h1>
  <p class="meta">Updated {html.escape(snapshot['generated_at'][:10])} · {len(records)} open/new tenders · {len(diff['added'])} new today</p>
  <a class="cta" href="{html.escape(checkout_url)}">Unlock Full Normalized CSV + JSON API ($40)</a>
  <table>
    <thead><tr><th>Published</th><th>Category</th><th>Closes</th><th>Tender</th></tr></thead>
    <tbody>{preview_rows}</tbody>
  </table>
</body>
</html>
"""
    (dist_dir / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    dist_dir = Path(os.environ.get("DIST_DIR", "dist"))
    checkout_url = os.environ.get("POLAR_CHECKOUT_URL", "https://polar.sh/")
    prev_path = dist_dir / "data" / "latest.json"
    previous: list[dict[str, str]] = []
    if prev_path.exists():
        previous = json.loads(prev_path.read_text(encoding="utf-8")).get("records", [])

    ckan_payload = json.loads(fetch_text(CKAN_DATASET_URL))
    csv_url = resolve_canadabuys_csv_url(ckan_payload)
    csv_text = fetch_text(csv_url)
    records = normalize_csv_rows(csv_text)
    diff = compute_diff(records, previous)
    write_outputs(records, diff, dist_dir, checkout_url)
    print(f"OK: wrote {len(records)} CanadaBuys records ({len(diff['added'])} added)")


if __name__ == "__main__":
    main()