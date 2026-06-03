import duckdb as dd
import pandas as pd
import numpy as np
from datetime import date

conn = dd.connect("dagher.duckdb")



def simple_returns(conn: dd.DuckDBPyConnection, ticker: str) -> pd.Series:
    close_df = conn.execute(
        "SELECT date, close FROM prices WHERE ticker = ? ORDER BY Date", 
        [ticker]
        ).df()
    
    returns = close_df['close'].pct_change()
    return returns

def log_returns(conn: dd.DuckDBPyConnection, ticker: str) -> pd.Series:
    log_df = conn.execute(
        "SELECT Date, close FROM prices WHERE ticker = ? ORDER BY Date",
        [ticker]).df()
    
    log_returns = np.log(log_df["close"] / log_df["close"].shift(1))

    return log_returns

def cumulative_returns(conn: dd.DuckDBPyConnection, ticker: str, start_date: str, end_date: str) -> float:
    old_price = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date >= ? ORDER BY Date LIMIT 1",
        [ticker, start_date]
    ).fetchone()[0]

    new_price = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date <= ? ORDER BY Date DESC LIMIT 1",
        [ticker, end_date]
    ).fetchone()[0]
    print(f"Start price ({start_date}): {old_price}")
    print(f"End price ({end_date}): {new_price}")
    returns = (new_price - old_price) / old_price
    return returns

def volatility(returns: pd.series) -> float:
    daily_vol = np.std(returns)
    annual_vol = daily_vol * np.sqrt(252)
    return annual_vol

def annualized_return(conn: dd.DuckDBPyConnection, ticker: str, start_date: str, end_date: str) -> float:
    start_price = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date >= ? ORDER BY date LIMIT 1",
        [ticker, start_date]).fetchone()[0]
    end_price = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date <= ? ORDER BY date DESC",
        [ticker, end_date]).fetchone()[0]
    
    conn_size = conn.execute("SELECT COUNT(*) FROM prices WHERE ticker = ?", [ticker]).fetchone()[0]
    years = conn_size / 252
    annualized_return = ((end_price / start_price) ** (1 / years)) - 1

    print(f"From {start_date} to {end_date}, annualized return is: {annualized_return}")
    return annualized_return




annualized_return(conn, 'AMZN', "2024-01-01", "2024-12-31")

