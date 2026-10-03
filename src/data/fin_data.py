# For later

import duckdb as dd
import pandas as pd
import yfinance as yf


# 10-year US Treasury yield (risk-free rate proxy)
# Update pei riodically or replace with live fetch
RISK_FREE_RATE = 0.043

from src.utils.stock_models import Company



def create_raw_fundementals_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fundementals_raw(
            -- Identifiers & Temporal Metadata
            ticker VARCHAR,
            fiscal_period_end DATE,
            filing_available_date DATE,

            -- Income Statement (Temporary / Nominal Accounts)
            revenue FLOAT,
            cogs FLOAT,
            gross_profit FLOAT,
            ebit FLOAT,
            dep_amort FLOAT,
            interest_expense FLOAT,
            net_income FLOAT,

            -- Balance Sheet: Assets (Permanent / Real Accounts)
            cash FLOAT,
            current_assets FLOAT,
            total_assets FLOAT,

            -- Balance Sheet: Liabilities (Permanent / Real Accounts)
            current_liabilities FLOAT,
            total_debt FLOAT,
            total_liabilities FLOAT,

            -- Balance Sheet: Equity (Permanent / Real Accounts)
            preferred_equity FLOAT,
            equity FLOAT,
            retained_earnings FLOAT,
            shares_outstanding FLOAT,

            -- Cash Flow Statement & Capital Allocation
            cfo FLOAT,
            capex FLOAT,
            dividends_paid FLOAT,
            buybacks FLOAT,
            debt_repaid FLOAT,

            -- Derived / Working Metrics
            working_capital FLOAT,
            net_assets FLOAT
            )
    """)

def append_raw_fundementals(conn: dd.DuckDBPyConnection, ticker: str) -> None:
    pass