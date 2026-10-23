"""Indeed Hiring Lab AI Tracker (CC BY 4.0, attribution "Source: Indeed Hiring Lab").

AI_posting.csv holds a daily 7-day trailing average of the share (%) of job postings that
mention AI terms, per country (ISO-2 `jobcountry`). It is aggregated here to a monthly mean.
Malaysia and Singapore are not in the data; the UI never labels it as Malaysia.
"""

import csv
import io
from collections import defaultdict

import httpx

TIMEOUT_S = 60.0
SHARE_COLUMN_SUFFIX = "_share_postings"  # e.g. AI_share_postings; GenAI if it appears later
DECIMALS = 3

COUNTRY_NAMES = {
    "AU": "Australia",
    "CA": "Canada",
    "DE": "Germany",
    "FR": "France",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "IT": "Italy",
    "NL": "Netherlands",
    "US": "United States",
}


def fetch_csv(url: str, client: httpx.Client) -> str:
    response = client.get(url, timeout=TIMEOUT_S, follow_redirects=True)
    response.raise_for_status()
    return response.text


def share_columns(fieldnames: list[str]) -> list[str]:
    return [f for f in fieldnames if f.endswith(SHARE_COLUMN_SUFFIX)]


def monthly_means(csv_text: str) -> tuple[dict[str, dict[str, dict[str, float]]], str]:
    """{series: {country: {YYYY-MM: mean}}} and the latest date in the data (data_as_of)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    columns = share_columns(list(reader.fieldnames or []))
    if not columns:
        raise ValueError("no *_share_postings column in the Indeed CSV")
    sums: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    latest = ""
    for row in reader:
        date, country = row["date"], row["jobcountry"]
        latest = max(latest, date)
        for col in columns:
            if row.get(col):
                sums[(col, country, date[:7])].append(float(row[col]))
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for (col, country, month), values in sorted(sums.items()):
        series = col.removesuffix(SHARE_COLUMN_SUFFIX)
        out[series][country][month] = round(sum(values) / len(values), DECIMALS)
    return {s: dict(c) for s, c in out.items()}, latest
