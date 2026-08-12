# For later

import duckdb as dd
import pandas as pd
import yfinance as yf


# 10-year US Treasury yield (risk-free rate proxy)
# Update periodically or replace with live fetch
RISK_FREE_RATE = 0.043

from src.utils.stock_models import Company



def create_raw_fundementals_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTs fundementals_raw(
            ticker VARCHAR,
            fiscal_period_end DATE,
            filing_available_date DATE,
            revenue FLOAT,
            cogs FLOAT,
            ebit FLOAT,
            net_income FLOAT,
            cfo FLOAT,
            net_assets FLOAT,
            total_liabilities FLOAT,
            working_capital FLOAT,
            retained_earnings FLOAT,
            cash FLOAT,
            total_debt FLOAT,
            preferred_equity FLOAT,
            shares_outstanding FLOAT,
            dividends_paid FLOAT,
            buybacks FLOAT,
            debt_repaid FLOAT
            )
    """)

def append_raw_fundementals(conn: dd.DuckDBPyConnection, ticker: str) -> None:

    



#     conn.execute(
#         "INSERT INTO fundementals_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
#         []
#     )