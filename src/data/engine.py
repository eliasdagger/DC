import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

from src.utils.models import Client, Stock
from src.data.clients import create_clients_table, add_client, get_client_data
from src.data.holdings import create_holdings_table, add_holdings
from src.data.ingestion import get_prices, cache_prices
from src.features.returns import simple_returns, log_returns, cumulative_returns, annualized_return, volatility


# ── Database Connection ───────────────────────────────────────────────────────
conn = dd.connect('dagher.duckdb')


# ── Setup ─────────────────────────────────────────────────────────────────────
def setup_db(conn: dd.DuckDBPyConnection) -> None:
    """Initialize all DuckDB tables"""
    create_clients_table(conn)
    create_holdings_table(conn)
    print("Database initialized.")


# ── Client Operations ─────────────────────────────────────────────────────────
def onboard_client(conn: dd.DuckDBPyConnection, client: Client, stocks: list) -> None:
    """Create a client and add their holdings in one call"""
    add_client(conn, client)
    add_holdings(conn, stocks, client.client_id)
    print(f"Client {client.name} onboarded with {len(stocks)} holdings.")


# ── Market Data ───────────────────────────────────────────────────────────────
def ingest_prices(conn: dd.DuckDBPyConnection, ticker: str, start_date: str, end_date: str) -> None:
    """Fetch and cache market data for a ticker"""
    prices = get_prices(ticker, start_date, end_date)
    cache_prices(conn, prices, ticker)
    print(f"{ticker} prices cached from {start_date} to {end_date}.")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # Setup database
    setup_db(conn)

    # Create stocks
    stocks = [
        Stock(ticker="AMZN", shares=10, purchase_price=12.0, purchase_date=date(2024, 1, 1)),
        Stock(ticker="MSFT", shares=12, purchase_price=10.0, purchase_date=date(2024, 1, 1))
    ]

    # Create client
    c1 = Client(client_id=123, name="John", risk_tolerance="High", holdings=stocks, goals="Retirement")

    # Onboard client
    onboard_client(conn, c1, stocks)

    # Verify client data
    print(get_client_data(conn, c1).to_string())

    # Ingest market data
    ingest_prices(conn, "AMZN", "2024-01-01", "2024-12-31")
    ingest_prices(conn, "MSFT", "2024-01-01", "2024-12-31")

    # Calculate returns
    print(simple_returns(conn, "AMZN"))
    print(annualized_return(conn, "AMZN", "2024-01-01", "2024-12-31"))
    print(volatility(simple_returns(conn, "AMZN")))

    conn.close()