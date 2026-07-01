import duckdb as dd
import pandas as pd 
from src.utils.models import Client, Stock
from src.data.clients import get_client_data
from src.data.holdings import get_holdings
from src.features.returns import annualized_return, volatility, sharpe_ratio
conn = dd.connect('dagher.duckdb')

def generate_report(conn: dd.DuckDBPyConnection, client: Client, risk_free_rate: float, start_date: str, end_date: str) -> pd.DataFrame:
    df = pd.DataFrame()
    
    client_info = get_client_data(conn, client)

    client_holdings = get_holdings(conn, client.client_id)

    for __, idx in client_holdings.iterrows():
        sharpe = sharpe_ratio(conn, idx['ticker'], risk_free_rate, start_date, end_date)

