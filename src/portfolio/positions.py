import pandas as pd
import numpy as np
import duckdb as dd
from src.utils.models import Client, Stock
from src.features.returns import simple_returns, volatility, annualized_return, sharpe_ratio as single_sharpe
from src.data.ingestion import get_cached_price
from src.data.fin_data import RISK_FREE_RATE
from datetime import date


def compute_position_value(price: float, shares: float) -> float:
    return price * shares


def get_client_positions(conn: dd.DuckDBPyConnection, client_id: int) -> pd.DataFrame:    
    holdings = conn.execute("""
        SELECT 
            ticker, 
            SUM(shares) as shares, 
            AVG(purchase_price) as purchase_price, 
            SUM(dividends) as dividends
        FROM holdings
        WHERE client_id = ?
        GROUP BY ticker
        """,
        [client_id]
    ).df()

    rows = []
    
    for __, row in holdings.iterrows():
        ticker = row['ticker']
        shares = row['shares']
        purchase_price = row['purchase_price']
        current_price = get_cached_price(conn, ticker, date.today().strftime("%Y-%m-%d"))
        dividends = row['dividends']
        total_value = compute_position_value(current_price, shares)
        cost_basis = compute_position_value(purchase_price, shares)
        unrealized_gain = total_value - cost_basis

        rows.append({
            'Ticker': ticker,
            'Shares': shares,
            'Purchase-Price': purchase_price,
            'Current-Price': current_price,
            'Dividends': dividends,
            'Total-Value': total_value,
            'Unrealized-Gain': unrealized_gain
        })

    res = pd.DataFrame(rows)

    total = res['Total-Value'].sum()
    res['Weight'] = res['Total-Value'] / total

    return res


def portfolio_value(conn: dd.DuckDBPyConnection, client_id: int) -> float:
    positions = get_client_positions(conn, client_id)
    return positions['Total-Value'].sum()


def portfolio_sharpe(conn: dd.DuckDBPyConnection, client_id: int, start_date: str, end_date: str) -> float:
    positions = get_client_positions(conn, client_id)

    # Build weighted portfolio returns
    portfolio_returns = None
    for __, row in positions.iterrows():
        ticker = row['Ticker']
        weight = row['Weight']
        returns = simple_returns(conn, ticker)

        if portfolio_returns is None:
            portfolio_returns = returns * weight
        else:
            portfolio_returns = portfolio_returns + (returns * weight)

    # Sharpe on combined portfolio returns
    ann_return = (1 + portfolio_returns.mean()) ** 252 - 1
    vol = volatility(portfolio_returns)
    sharpe = (ann_return - RISK_FREE_RATE) / vol
    return sharpe


def max_drawdown(conn: dd.DuckDBPyConnection, ticker: str) -> float:
    returns = simple_returns(conn, ticker).dropna()
    cumulative = (1 + returns).cumprod()
    rolling_peak = cumulative.cummax()
    drawdown = (cumulative - rolling_peak) / rolling_peak
    return drawdown.min()


if __name__ == "__main__":
    conn = dd.connect('dagher.duckdb')

    print("\n=== Client Positions ===")
    print(get_client_positions(conn, 123).to_string())

    print("\n=== Portfolio Value ===")
    print(f"${portfolio_value(conn, 123):,.2f}")

    print("\n=== Portfolio Sharpe ===")
    print(f"{portfolio_sharpe(conn, 123, '2024-01-01', '2024-12-31'):.2f}")

    print("\n=== Max Drawdown (AMZN) ===")
    print(f"{max_drawdown(conn, 'AMZN'):.2%}")