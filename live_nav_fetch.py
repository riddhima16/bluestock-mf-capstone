"""
live_nav_fetch.py
Day 1 — Task 4 & 5

What this script does:
    - Calls the free public mfapi.in API to get NAV history for 6 mutual fund schemes
    - Converts the JSON response into a Pandas DataFrame
    - Saves each scheme's NAV history as a CSV file in data/raw/

NAV = Net Asset Value = the "price" of one unit of a mutual fund on a given day.
AMFI code = a unique number that identifies each mutual fund scheme in India.

No API key or login is needed. mfapi.in is a free public API.
"""

import requests          # for making HTTP GET requests to the API
import pandas as pd      # for working with data tables
import time              # to add a small pause between API calls (be polite!)
from pathlib import Path # for handling file paths cleanly

# ── Where to save the raw CSV files ──────────────────────────────────────────
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)  # creates folder if it doesn't exist

# ── The 6 fund schemes we want to fetch ──────────────────────────────────────
# Format: AMFI scheme code → a short label used for the output filename
SCHEMES = {
    125497: "hdfc_top_100_direct",   # Task 4 (HDFC Top 100)
    119551: "sbi_bluechip",          # Task 5 — scheme 1
    120503: "icici_bluechip",        # Task 5 — scheme 2
    118632: "nippon_large_cap",      # Task 5 — scheme 3
    119092: "axis_bluechip",         # Task 5 — scheme 4
    120841: "kotak_bluechip",        # Task 5 — scheme 5
}

# ── API URL pattern ───────────────────────────────────────────────────────────
# Replace {code} with the actual scheme code, e.g. https://api.mfapi.in/mf/125497
BASE_URL = "https://api.mfapi.in/mf/{code}"


def fetch_nav_data(scheme_code: int) -> dict:
    """
    Makes a GET request to mfapi.in for the given scheme code.
    Returns the full JSON response as a Python dictionary.
    """
    url = BASE_URL.format(code=scheme_code)
    print(f"  Calling API: {url}")
    response = requests.get(url, timeout=15)  # wait max 15 seconds for a reply
    response.raise_for_status()               # crash loudly if HTTP error (404, 500, etc.)
    return response.json()                    # convert JSON text → Python dict


def parse_to_dataframe(api_response: dict, scheme_code: int) -> pd.DataFrame:
    """
    The API returns a dict with two keys:
      - "meta"  : dict with fund_house, scheme_name, scheme_category, etc.
      - "data"  : list of {"date": "DD-MM-YYYY", "nav": "123.4500"} dicts

    This function turns the "data" list into a clean DataFrame and adds
    metadata columns from "meta".
    """
    meta    = api_response.get("meta", {})
    records = api_response.get("data", [])

    if not records:
        print(f"  WARNING: No NAV records found for scheme {scheme_code}")
        return pd.DataFrame()

    df = pd.DataFrame(records)  # each dict in the list becomes a row

    # Convert date string "DD-MM-YYYY" → proper datetime object
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")

    # Convert NAV from string "892.4500" → float 892.45
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    # Add identifying columns from the metadata
    df["amfi_code"]        = scheme_code
    df["scheme_name"]      = meta.get("scheme_name")
    df["fund_house"]       = meta.get("fund_house")
    df["scheme_category"]  = meta.get("scheme_category")

    # Sort oldest → newest and reset row numbers
    df = df.sort_values("date").reset_index(drop=True)

    # Keep columns in a sensible order
    return df[["amfi_code", "scheme_name", "fund_house", "scheme_category", "date", "nav"]]


def main():
    print("=" * 55)
    print("  live_nav_fetch.py — Fetching NAV data from mfapi.in")
    print("=" * 55)

    summary_rows = []

    for code, label in SCHEMES.items():
        print(f"\nFetching: {label} (code={code})")
        try:
            api_response = fetch_nav_data(code)
            df = parse_to_dataframe(api_response, code)

            # Save to data/raw/ with a clear filename
            output_path = RAW_DIR / f"nav_{label}.csv"
            df.to_csv(output_path, index=False)

            print(f"  Saved {len(df)} rows  →  {output_path}")
            print(f"  Date range: {df['date'].min().date()}  to  {df['date'].max().date()}")
            print(f"  Latest NAV: ₹{df['nav'].iloc[-1]:.4f}")

            summary_rows.append({
                "amfi_code": code,
                "label":     label,
                "status":    "SUCCESS",
                "rows":      len(df),
                "latest_nav": df["nav"].iloc[-1],
            })

        except requests.RequestException as e:
            print(f"  ERROR: Could not fetch data — {e}")
            summary_rows.append({
                "amfi_code": code,
                "label":     label,
                "status":    "FAILED",
                "rows":      0,
                "latest_nav": None,
            })

        time.sleep(0.5)  # small pause so we don't spam the free API

    # Print a final summary table
    print("\n" + "=" * 55)
    print("  FETCH SUMMARY")
    print("=" * 55)
    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))
    print("\nAll done! Check data/raw/ for the new CSV files.")


if __name__ == "__main__":
    main()