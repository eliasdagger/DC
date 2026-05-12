"""
Module: Data Ingestion

Problem:
Portfolio analytics require live market data. Manual data entry is error-prone and a long process.

Description:
Fetches historical price data from yfinance and caches to DuckDB.

Key Functions:
- get_prices: Fetch OHLCV data for a ticker
- cache_prices: Store prices in DuckDB
- get_cached_price: Retrieve price from cache

Dependencies:
- yfinance: For market data
- pandas: For data handling
- duckdb: For caching

Example:
    >>> prices = get_prices('AAPL', '2024-01-01', '2024-12-31')
"""
import pandas as pd
import duckdb as dd
import yfinance as yf
from datetime import date

def get_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    ticker_name = yf.Ticker[ticker]
    # .history() --> pd.DataFrame()
    prices = ticker_name.history(start = start_date, end = end_date)
    return prices


def cache_prices(conn: dd.DuckDBPyConnection, prices: pd.DataFrame, ticker: str) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
                 ticker VARCHAR, 
                 date DATE, 
                 open FLOAT,
                 high FLOAT,
                 low FLOAT,
                 close FLOAT,
                 volume INTEGER       
        )
    """)

    for idx, row in prices.iterrows():
        conn.execute(
            "INSERT INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)",
            [ticker, idx.date(), row['open'], row['high'], row['Low'], row['Close'], row['Volume']]
        )
    
        
def get_cached_price(conn: dd.DuckDBPyConnection, ticker: str, date_str: str) -> float:
    result = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date = ?",
        [ticker, date_str]
    # get the first result
    ).fetchone()
    
    return result[0] if result else None


if __name__ == "__main__":
    conn = dd.connect('dagher.duckdb')
    
    prices = get_prices("AAPL", "2024-01-01", "2024-12-31")
    print(prices.head())
    
    cache_prices(conn, prices, "AAPL")
    print("Cached.")

    conn.close()


