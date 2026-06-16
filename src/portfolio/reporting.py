import duckdb as dd
import pandas as pd 
from src.utils.models import Client, Stock
from src.data.clients import get_client_data
conn = dd.connect('dagher.duckdb')

def report_info(conn: dd.DuckDBPyConnection, client: Client) -> pd.DataFrame:
    client_info = get_client_data(conn, client)

    





    