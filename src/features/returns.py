"""
Module: Return Calculations

Problem:
What is the purpose of structuring and storing data? returns.py serves to handle client's stocks
to deliver returns with various financial return metrics for performance transparency.   

Description:
Accesses dagher.duckdb queries data for specific tickers and date ranges, then calculates returns.
Key Functions:
- simple_returns: Returns % change month over month, derived from closing price over a specific date range. 
- log_returns: Calculates log return (ln(currentValue / initialValue)) 
- cumulative_returns: Returns total % gained/lost over period
- volatility: Calculates volatility by multiplying trading days by stock stdev (swing movement)
- annualized_return: Calculates stocks avg YoY return by attaining initialValue and currentValue/endValue and averaging gains by years held 

Dependencies:
- duckdb: For querying cached price data
- pandas: For time-series manipulation
- numpy: For vectorized math

Example:
    >>> [one working example]
"""
import duckdb as dd
import pandas as pd
import numpy as np
from datetime import date

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

def volatility(returns: pd.Series) -> float:
    daily_vol = np.std(returns)
    annual_vol = daily_vol * np.sqrt(252)
    return annual_vol

def annualized_return(conn: dd.DuckDBPyConnection, ticker: str, start_date: str, end_date: str) -> float:
    start_price = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date >= ? ORDER BY date LIMIT 1",
        [ticker, start_date]).fetchone()[0]
    end_price = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
        [ticker, end_date]).fetchone()[0]
    
    conn_size = conn.execute("SELECT COUNT(*) FROM prices WHERE ticker = ?", [ticker]).fetchone()[0]
    years = conn_size / 252
    annualized_return = ((end_price / start_price) ** (1 / years)) - 1

    print(f"From {start_date} to {end_date}, annualized return is: {annualized_return}")
    return annualized_return

def sharpe_ratio(conn: dd.DuckDBPyConnection, ticker: str, risk_free_rate: float, start_date: str, end_date: str) -> float:
    roi = annualized_return(conn, ticker, start_date, end_date)
    returns = simple_returns(conn, ticker)
    vol = volatility(returns)

    sharpe = (roi - risk_free_rate) / vol
    return sharpe
    

def max_drawdown(conn: dd.DuckDBPyConnection, ticker: str) -> float:
    returns = simple_returns(conn, ticker).dropna()

    # cumulative product calculates the current 'price' based off percent change. add 1 to normalize
    cumprod = (1 + returns).cumprod()

    peak = cumprod.cummax()

    drawdown = ((cumprod - peak) / peak) * 100

    max_dd = drawdown.min()
    return max_dd

# NOTE - ADD TO ENGINE LATER
conn = dd.connect('dagher.duckdb')
# print(f"sharpe = {sharpe_ratio(conn, "AMZN", 0.043, "2024-01-01", "2024-12-31")}")
# print(f"drawdown = {max_drawdown(conn, "AMZN")}")