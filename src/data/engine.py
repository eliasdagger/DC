"""
Module: Data Engine

Problem:
Creating clients, holdings, and ingesting market data requires calling
functions across multiple modules. This creates messy imports and repeated
setup code across files.

Description:
Single entry point for all data operations. Initializes database tables,
creates clients, adds holdings, and fetches/caches market data through
one unified interface.

Key Functions:
- setup_db: Initialize all DuckDB tables
- onboard_client: Create client + holdings in one call
- ingest_prices: Fetch and cache market data for a ticker

Dependencies:
- clients.py: Client database operations
- holdings.py: Holdings database operations
- ingestion.py: Market data fetching and caching

Example:
    >>> conn = dd.connect('dagher.duckdb')
    >>> setup_db(conn)
    >>> onboard_client(conn, c1, stocks)
    >>> ingest_prices(conn, "AMZN", "2024-01-01", "2024-12-31")
"""

import duckdb as dd
from datetime import date

from src.utils.operations_models import Client
from src.utils.stock_models import Stock, Company
from src.data.clients import create_clients_table, add_client, get_client_data
from src.data.holdings import create_holdings_table, add_holdings
from src.data.ingestion import get_prices, cache_prices, get_cached_price
from src.features.returns import simple_returns, log_returns, cumulative_returns, annualized_return, volatility
from src.portfolio.reporting import generate_report
from src.data.companies import create_company_attributes_table, append_company, get_company_attributes

# ── Initialize Database Connection ──────────────────────────────────────────────────────────────────
conn = dd.connect('dagher.duckdb')

# ── Setup DuckDB Tables ──────────────────────────────────────────────────────────────────
def initialize_database(conn: dd.DuckDBPyConnection) -> None:
    create_company_attributes_table(conn)
    create_clients_table(conn)
    create_holdings_table(conn)
    create_company_attributes_table(conn)
    print("Database Initilized in dagher.duckdb")
    
# ── Initialize Client Data ──────────────────────────────────────────────────────────────────
def create_client(conn: dd.DuckDBPyConnection, client: Client, stocks: Stock) -> None:
    add_client(conn, client)
    add_holdings(conn, stocks, client.client_id)
    print(f"Successfully, added {len(stocks)} under {client.name}. ID={client.client_id}")

# ── Initialize Company Data ──────────────────────────────────────────────────────────────────
def create_company(conn: dd.DuckDBPyConnection, company: Company) -> None:
    append_company(conn, company)
    print(f"Successfully added {company.name} to companies table")

# ── Finanical Metric and Market Data Ingestion ──────────────────────────────────────────────────────────────────
def add_prices_data(conn: dd.DuckDBPyConnection, ticker: str, start_date: str, end_date: str) -> None:
    prices = get_prices(ticker, start_date, end_date)
    cache_prices(conn, prices, ticker)
    print(f"{ticker} prices cached from {start_date} to {end_date}.")

# ── Main Method ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    ticker1 = "AMZN"
    ticker2 = "AAPL"
    
    start_date = '2025-01-01'
    end_date = '2025-12-31'

    # Ingest Prices Data (must happen before building Stock objects that read cached prices)
    add_prices_data(conn, ticker1, start_date, end_date)
    add_prices_data(conn, ticker2, start_date, end_date)

    stocks = [Stock(ticker=ticker1, shares=10, purchase_date=start_date, purchase_price=get_cached_price(conn, ticker1, end_date)),
                  Stock(ticker=ticker2, shares=10, purchase_date=start_date, purchase_price=get_cached_price(conn, ticker2, end_date), sale_date='2025-06-01', sale_price=get_cached_price(conn, ticker2, '2025-06-01'))
        ]

    client1 = Client(client_id=1, name='John', risk_tolerance='medium', holdings=stocks,
                            #  age=None, holdings_value=, total_holdings=, cash_position=, considerations=None
                             goals='Saving for retirement'
                             )

    company = Company(name="Amazon", ticker="AMZN", sector="Consumer", industry="Retail", company_type="Mature")
    
    # Create DuckDB Tables
    initialize_database(conn)

    # Append and Portray Company
    create_company(conn, company)   
    print(get_company_attributes(conn, ticker1).to_string())   

    # Create and Portray Client
    create_client(conn, client1, stocks)
    print(get_client_data(conn, client1.client_id).to_string())

    # Calculate returns
    print(simple_returns(conn, "AMZN"))
    print(annualized_return(conn, "AMZN", start_date, end_date))
    print(volatility(simple_returns(conn, "AMZN")))

    # generate_report(conn, 1, start_date, end_date)    
    
