import pandas as pd
import numpy as np
import duckdb as dd
from src.utils.models import Client, Stock
from src.features.returns import simple_returns, volatility

def get_client_positions(conn, client_id) -> pd.DataFrame:
    positions = conn.execute(
        "SELECT ticker FROM holdings WHERE ticker = ?",
        [client_id.ticker]
    )
    
    return positions

def compute_position_value(conn, ticker, shares) -> float:
    """Current market value of a position"""
    pass

def portfolio_value(conn, client_id) -> float:
    """Total portfolio value for a client"""
    pass

def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    """Risk-adjusted return metric"""
    pass

def max_drawdown(returns: pd.Series) -> float:
    """Largest peak-to-trough decline"""
    pass


