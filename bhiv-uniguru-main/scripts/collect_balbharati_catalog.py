from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "masterdb" / "balbharti" / "official_catalog"
SITE_URL = "https://books.ebalbharati.in/"
PDF_HOST = "https://ebooks.ebalbharati.in/pdfs/"
COVER_HOST = "https://books.ebalbharati.in/BookCovers/"
VIEWSTATE_FIELDS = ("__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR")
FILTER_GROUPS = {
    100: "book_type",
    200: "standard",
    300: "medium",
    400: "subject",
}
FILTER_GROUP_LABELS = {
    "book_type": "Book Types",
    "standard": "Standards",
    "medium": "Mediums",
    "subject": "Subjects",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def extract_hidden_fields(html: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for name in VIEWSTATE_FIELDS:
        match = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]*)"', html)
        if match:
            fields[name] = unescape(match.group(1))
    return fields


def parse_years(html: str) -> list[str]:
    years = re.findall(r'chkclickradio\("(\d{4})"\)', html)
    return sorted(set(years), reverse=True)


def parse_total_books(html: str) -> int:
    match = re.search(r'<span id="lblBox" class="lblDesign">(\d+)</span>', html)
    if not match:
        raise ValueError("Could not find total book count in catalog page.")
    return int(match.group(1))


def parse_total_pages(html: str) -> int:
    match = re.search(r'<span id="lblNoOfPages" class="lblDesign">(\d+)</span>', html)
    if not match:
        total_books = parse_total_books(html)
        return 0 if total_books == 0 else 1
    return int(match.group(1))


def parse_filter_taxonomy(html: str) -> dict[str, Any]:
    option_pattern = re.compile(
        r"<input id='chk_(\d+)' type='checkbox'[^>]*>\s*"
        r"<label[^>]*>\s*<div[^>]*></div>\s*<div class='[^']+'>(.*?)</div>",
        re.S,
    )
    grouped: dict[str, list[dict[str, str]]] = {name: [] for name in FILTER_GROUP_LABELS}
    for option_id_raw, label_raw in option_pattern.findall(html):
        option_id = int(option_id_raw)
        group_code = (option_id // 100) * 100
        group_name = FILTER_GROUPS.get(group_code)
        if not group_name:
            continue
        grouped[group_name].append(
            {
                "site_option_id": str(option_id),
                "label": normalize_text(label_raw),
            }
        )

    for group_name in grouped:
        grouped[group_name] = sorted(grouped[group_name], key=lambda row: int(row["site_option_id"]))

    return {
        "schema": "UNIGURU_BALBHARTI_SITE_TAXONOMY_V1",
        "collected_at": utc_now_iso(),
        "source_site": SITE_URL,
        "groups": [
            {
                "group_name": group_name,
                "group_label": FILTER_GROUP_LABELS[group_name],
                "site_group_code": next(code for code, name in FILTER_GROUPS.items() if name == group_name),
                "options": grouped[group_name],
            }
            for group_name in ("book_type", "standard", "medium", "subject")
        ],
    }


def parse_books(html: str, year: str, page_number: int) -> list[dict[str, Any]]:
    card_pattern = re.compile(
        r"openpdf\((\d+)\).*?"
        r"src=BookCovers/([^\"' >]+).*?"
        r"<div class=divbooknm title='([^']*)'>(.*?)</div>.*?"
        r'SaveToDisk\("([^"]+)","([^"]+)"\)',
        re.S,
    )
    books: list[dict[str, Any]] = []
    for display_index, match in enumerate(card_pattern.finditer(html), start=1):
        book_id, cover_name, title_attr, title_html, pdf_url, pdf_name = match.groups()
        title = normalize_text(title_attr or title_html)
        record = {
            "catalog_record_id": f"BALBHARTI_SITE_{year}_{book_id}",
            "year": year,
            "book_id": book_id,
            "title": title,
            "pdf_url": pdf_url,
            "pdf_open_url": f"{SITE_URL}pdfOpen.aspx?itemid={book_id}",
            "pdf_download_tracking_url": f"{SITE_URL}pdfdownload.aspx?itemid={book_id}",
            "pdf_file_name": pdf_name,
            "cover_url": f"{COVER_HOST}{cover_name}",
            "catalog_page_number": page_number,
            "display_index_on_page": display_index,
            "source_site": SITE_URL,
        }
        record["record_hash"] = sha256_json(record)
        books.append(record)
    return books


class BalbharatiCatalogClient:
    def __init__(self, throttle_seconds: float = 0.0, timeout_seconds: int = 30) -> None:
        self.session = requests.Session()
        self.throttle_seconds = throttle_seconds
        self.timeout_seconds = timeout_seconds

    def request(self, method: str, data: dict[str, str] | None = None) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.request(method, SITE_URL, data=data, timeout=self.timeout_seconds)
                response.raise_for_status()
                response.encoding = "utf-8"
                if self.throttle_seconds:
                    time.sleep(self.throttle_seconds)
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(1.0 + attempt)
        raise RuntimeError(f"Failed to fetch Balbharati catalog page: {last_error}") from last_error

    def get_root(self) -> str:
        return self.request("GET")

    def postback(self, html: str, event_target: str, event_argument: str, txt_selected: str, year: str) -> str:
        payload = extract_hidden_fields(html)
        payload["__EVENTTARGET"] = event_target
        payload["__EVENTARGUMENT"] = event_argument
        payload["txtSelected"] = txt_selected
        payload["txtyear"] = year
        return self.request("POST", data=payload)

    def select_year(self, initial_html: str, year: str) -> str:
        default_year_match = re.search(r'<input name="txtyear" type="text" id="txtyear" style="display:none;" value="(\d{4})"', initial_html)
        default_year = default_year_match.group(1) if default_year_match else None
        if year == default_year:
            return initial_html
        return self.postback(initial_html, "lnkradioclick", "", "", year)

    def collect_year_catalog(self, year: str) -> dict[str, Any]:
        initial_html = self.get_root()
        current_html = self.select_year(initial_html, year)
        total_books = parse_total_books(current_html)
        total_pages = parse_total_pages(current_html)
        books: list[dict[str, Any]] = []
        seen_book_ids: set[str] = set()
        for page_number in range(1, total_pages + 1):
            if page_number > 1:
                current_html = self.postback(current_html, "upMain", f"#{page_number}", "", year)
            page_books = parse_books(current_html, year=year, page_number=page_number)
            for row in page_books:
                if row["book_id"] in seen_book_ids:
                    continue
                seen_book_ids.add(row["book_id"])
                books.append(row)
        books = sorted(books, key=lambda row: int(row["book_id"]))
        payload = {
            "schema": "UNIGURU_BALBHARTI_OFFICIAL_SITE_YEAR_CATALOG_V1",
            "collected_at": utc_now_iso(),
            "collection_method": "ASP.NET postback catalog traversal from official eBalbharati website",
            "source_site": SITE_URL,
            "pdf_host": PDF_HOST,
            "year": year,
            "books_on_site": total_books,
            "pages_on_site": total_pages,
            "book_count_collected": len(books),
            "books": books,
        }
        payload["dataset_hash"] = sha256_json({"year": year, "books": books})
        return payload

    def collect_filter_membership(self, year: str, taxonomy: dict[str, Any]) -> dict[str, Any]:
        initial_html = self.get_root()
        year_html = self.select_year(initial_html, year)
        memberships: dict[str, dict[str, list[dict[str, str]]]] = {}
        filter_option_books: list[dict[str, Any]] = []

        for group in taxonomy["groups"]:
            group_name = group["group_name"]
            for option in group["options"]:
                selected = option["site_option_id"]
                current_html = self.postback(year_html, "upBtn", f"{selected}#1", selected, year)
                total_books = parse_total_books(current_html)
                total_pages = parse_total_pages(current_html)
                option_book_ids: list[str] = []
                seen_ids: set[str] = set()
                for page_number in range(1, total_pages + 1):
                    if page_number > 1:
                        current_html = self.postback(current_html, "upMain", f"{selected}#{page_number}", selected, year)
                    page_books = parse_books(current_html, year=year, page_number=page_number)
                    for row in page_books:
                        book_id = row["book_id"]
                        if book_id in seen_ids:
                            continue
                        seen_ids.add(book_id)
                        option_book_ids.append(book_id)
                        memberships.setdefault(
                            book_id,
                            {name: [] for name in FILTER_GROUP_LABELS},
                        )[group_name].append(
                            {
                                "site_option_id": selected,
                                "label": option["label"],
                            }
                        )

                filter_option_books.append(
                    {
                        "group_name": group_name,
                        "group_label": group["group_label"],
                        "site_option_id": selected,
                        "label": option["label"],
                        "books_on_site": total_books,
                        "pages_on_site": total_pages,
                        "book_ids": sorted(option_book_ids, key=int),
                    }
                )

        books_index = [
            {
                "book_id": book_id,
                "matched_filters": memberships[book_id],
            }
            for book_id in sorted(memberships, key=int)
        ]
        payload = {
            "schema": "UNIGURU_BALBHARTI_OFFICIAL_SITE_FILTER_MEMBERSHIP_V1",
            "collected_at": utc_now_iso(),
            "collection_method": "Single-filter catalog traversal from official eBalbharati website",
            "source_site": SITE_URL,
            "year": year,
            "filter_option_books": filter_option_books,
            "books_index": books_index,
        }
        payload["dataset_hash"] = sha256_json(
            {
                "year": year,
                "filter_option_books": filter_option_books,
                "books_index": books_index,
            }
        )
        return payload


def enrich_catalog(year_catalog: dict[str, Any], filter_membership: dict[str, Any]) -> dict[str, Any]:
    membership_index = {
        row["book_id"]: row["matched_filters"]
        for row in filter_membership["books_index"]
    }
    books: list[dict[str, Any]] = []
    for row in year_catalog["books"]:
        enriched = dict(row)
        enriched["site_filter_membership"] = membership_index.get(
            row["book_id"],
            {name: [] for name in FILTER_GROUP_LABELS},
        )
        enriched["enriched_record_hash"] = sha256_json(enriched)
        books.append(enriched)

    payload = {
        "schema": "UNIGURU_BALBHARTI_OFFICIAL_SITE_ENRICHED_CATALOG_V1",
        "collected_at": utc_now_iso(),
        "source_site": SITE_URL,
        "year": year_catalog["year"],
        "books_on_site": year_catalog["books_on_site"],
        "pages_on_site": year_catalog["pages_on_site"],
        "book_count_collected": year_catalog["book_count_collected"],
        "books": books,
    }
    payload["dataset_hash"] = sha256_json({"year": payload["year"], "books": books})
    return payload


def build_summary(
    year_catalogs: list[dict[str, Any]],
    taxonomy: dict[str, Any],
    enrich_years: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    year_summaries = [
        {
            "year": payload["year"],
            "books_on_site": payload["books_on_site"],
            "pages_on_site": payload["pages_on_site"],
            "book_count_collected": payload["book_count_collected"],
            "dataset_hash": payload["dataset_hash"],
            "books_file": f"year_{payload['year']}_catalog.json",
        }
        for payload in sorted(year_catalogs, key=lambda row: row["year"], reverse=True)
    ]
    total_books = sum(row["book_count_collected"] for row in year_summaries)
    summary = {
        "schema": "UNIGURU_BALBHARTI_OFFICIAL_SITE_COLLECTION_SUMMARY_V1",
        "collected_at": utc_now_iso(),
        "source_site": SITE_URL,
        "output_dir": str(output_dir.relative_to(ROOT).as_posix()),
        "years_collected": [row["year"] for row in year_summaries],
        "total_books_collected_across_years": total_books,
        "taxonomy_file": "site_taxonomy.json",
        "enriched_years": sorted(enrich_years, reverse=True),
        "year_summaries": year_summaries,
        "filter_groups": [
            {
                "group_name": group["group_name"],
                "group_label": group["group_label"],
                "option_count": len(group["options"]),
            }
            for group in taxonomy["groups"]
        ],
    }
    summary["dataset_hash"] = sha256_json(summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect official Balbharati catalog datasets from books.ebalbharati.in.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated dataset files.",
    )
    parser.add_argument(
        "--years",
        nargs="*",
        default=None,
        help="Specific syllabus years to collect. Defaults to every year exposed by the site.",
    )
    parser.add_argument(
        "--enrich-filter-years",
        nargs="*",
        default=["2026"],
        help="Years for which to collect filter membership and emit enriched catalogs.",
    )
    parser.add_argument(
        "--throttle-seconds",
        type=float,
        default=0.0,
        help="Optional delay between requests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    bootstrap_client = BalbharatiCatalogClient(throttle_seconds=args.throttle_seconds)
    root_html = bootstrap_client.get_root()
    taxonomy = parse_filter_taxonomy(root_html)
    available_years = parse_years(root_html)
    years = args.years or available_years
    enrich_years = [year for year in args.enrich_filter_years if year in years]

    year_catalogs: list[dict[str, Any]] = []
    for year in years:
        client = BalbharatiCatalogClient(throttle_seconds=args.throttle_seconds)
        catalog = client.collect_year_catalog(year)
        year_catalogs.append(catalog)
        write_json(output_dir / f"year_{year}_catalog.json", catalog)

    write_json(output_dir / "site_taxonomy.json", taxonomy)

    for year in enrich_years:
        client = BalbharatiCatalogClient(throttle_seconds=args.throttle_seconds)
        membership = client.collect_filter_membership(year, taxonomy)
        write_json(output_dir / f"year_{year}_filter_membership.json", membership)
        catalog = next(payload for payload in year_catalogs if payload["year"] == year)
        enriched = enrich_catalog(catalog, membership)
        write_json(output_dir / f"year_{year}_catalog_enriched.json", enriched)

    summary = build_summary(year_catalogs, taxonomy, enrich_years, output_dir)
    write_json(output_dir / "collection_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
