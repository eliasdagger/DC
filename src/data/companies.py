"""
Module: Company Characteristic Ingestion

Problem:
Companies will release their quarterly reports, providing up to date information on their financial health.
Appending company name, sector, industry, and type is redundant in this manner considering they don't shift often.
But they DO shift eventually — a company reclassifies from Early-Stage to Mature, and that changes
which pillar weights get applied. Overwriting the old value would lose that, and a backtest run over
2023 would score companies using their 2026 classification.

Description:
Fetches company attributes and caches to DuckDB as a slowly changing dimension: rows are appended,
never overwritten, and each carries the date it became true. Reads return whichever row was current
as of a given date, so historical scoring stays honest.

Key Functions:
- create_company_attributes_table: Create table in DuckDB
- append_company: Stores a company in DuckDB, but only if something actually changed
- get_company_attributes: Returns a company's attributes as they stood on a given date

Dependencies:
- pandas: For data handling
- duckdb: For caching

Example:
    >>> create_company_attributes_table(conn)
    >>> append_company(conn, Company(ticker='AMZN', name='Amazon', sector='Consumer',
    ...                              industry='Retail', company_type='Early-Stage'))
    >>> get_company_attributes(conn, 'AMZN')                  # current
    >>> get_company_attributes(conn, 'AMZN', '2024-06-01')    # as it stood then
"""
from datetime import date
from typing import Optional

import duckdb as dd
import pandas as pd

from src.utils.stock_models import Company

ATTRIBUTE_COLUMNS = ["name", "sector", "industry", "company_type"]


def create_company_attributes_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS companies(
            ticker VARCHAR,
            name VARCHAR,
            sector VARCHAR,
            industry VARCHAR,
            company_type VARCHAR,
            as_of_date DATE
        )
        """
    )
    print("companies table created!")


def append_company(conn: dd.DuckDBPyConnection, company: Company, as_of_date: Optional[str] = None) -> None:
    """Append a company row only if it differs from its latest entry. 
    This will allow for backtesting and companies type evolution over time"""
    if not as_of_date:
        as_of_date = date.today().strftime("%Y-%m-%d")

    latest = get_company_attributes(conn, company.ticker, as_of_date)

    if latest is not None:
        unchanged = all(latest[col] == getattr(company, col) for col in ATTRIBUTE_COLUMNS)
        if unchanged:
            print(f"{company.ticker} unchanged — nothing appended")
            return

    conn.execute(
        "INSERT INTO companies VALUES (?,?,?,?,?,?)",
        [company.ticker, company.name, company.sector,
         company.industry, company.company_type, as_of_date]
    )
    print(f"{company.name} appended to companies table (as of {as_of_date})")


def get_company_attributes(conn: dd.DuckDBPyConnection, ticker: str, as_of_date: Optional[str] = None) -> Optional[pd.Series]:
    if as_of_date is None:
        as_of_date = date.today().strftime("%Y-%m-%d")

    res = conn.execute(
        """
        SELECT * FROM companies
        WHERE ticker = ? AND as_of_date <= ?
        ORDER BY as_of_date DESC
        LIMIT 1
        """,
        [ticker, as_of_date]
    ).fetchdf()

    if res.empty:
        return None

    return res.iloc[0]


def get_company_history(conn: dd.DuckDBPyConnection, ticker: str) -> pd.DataFrame:
    return conn.execute(
        "SELECT * FROM companies WHERE ticker = ? ORDER BY as_of_date",
        [ticker]
    ).fetchdf()
