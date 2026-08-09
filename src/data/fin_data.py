# For later

import duckdb as dd
import yfinance as yf


# 10-year US Treasury yield (risk-free rate proxy)
# Update periodically or replace with live fetch
RISK_FREE_RATE = 0.043


# def bond

# def get_risk_free_rate() ->:
    


# def get_market_return():
#     pass


# def get_benchmark_prices():
#     pass

conn = dd.connect('test.duckdb')

def create_company_attributes_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS companies(
            ticker VARCHAR,
            name VARCHAR, 
            sector VARCHAR,
            type VARCHAR 
        )
    """)

def append_company(conn: dd.DuckDBPyConnection, company: Company) -> None:
    conn.execute(
        "INSERT INTO companies VALUES (?,?,?,?,?)",
        [company.ticker, company.name, company.sector, company.industry, company.type]
    )

def get_company_attributes(conn: dd.DuckDBPyConnection, ticker: str) -> pd.Series:
    res = conn.execute(
        "SELECT * FROM companies WHERE ticker = ?", 
        [ticker]).series()

    return res

company = Company(ticker='AMZN', name='Amazon', sector='1', industry='2', type='3')
create_company_attributes_table(conn)
append_company(conn, company)
get_company_attributes(conn, 'AMZN')

def create_financial_data_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXIST fundementals_raw(
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

# Functions Job is persistance, this is why we are passing through a pydantic model
def append_company_fundementals(conn: dd.DuckDBPyConnection, ticker: str) -> None:



    conn.execute(
        "INSERT INTO fundementals_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        []
    )