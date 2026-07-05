import pandas as pd
import numpy as np
import duckdb as dd
from src.utils.models import Client, Stock
from src.features.returns import simple_returns, volatility
from src.data.ingestion import get_cached_price
from datetime import date

def get_client_positions(conn, client_id) -> pd.DataFrame:
    positions = conn.execute("""
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
    
    res = pd.DataFrame(columns=['Ticker', 'Shares', 'Purchase-Price', 'Current-Price', 'Dividends', 'Total-Value'])

    for __, row in positions.iterrows():
        ticker = row['ticker']
        shares = row['shares']
        purchase_price = row['purchase_price']
        current_price = get_cached_price(conn, ticker, date=date.today())
        dividends = row['dividends']
        total_value = compute_position_value(current_price, shares)

        
        new_row = pd.DataFrame([
            {
                'Ticker': ticker,
                'Shares': shares,
                'Purchase-Price': purchase_price,
                'Current-Price': current_price,
                'Dividends': dividends,
                'Total-Value': total_value
            }
        ])
        res = pd.concat([res, new_row], ignore_index=True)
 
    return res
    

def compute_position_value(current_price: float, shares: float) -> float:
    return current_price * shares



def portfolio_value(conn: dd.DuckDBPyConnection, client_id: int) -> float:
    positions = get_client_positions(conn, client_id)
    total_value = positions['Total-Value'].sum()

    return total_value

def sharpe_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    """Risk-adjusted return metric"""
    pass

def max_drawdown(returns: pd.Series) -> float:
    """Largest peak-to-trough decline"""
    pass


conn = dd.connect('dagher.duckdb')