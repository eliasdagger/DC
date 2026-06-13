import pandas as pd
import duckdb as dd
import numpy as np
from datetime import date
from typing import List, Optional

# from src.utils.models import Client, Stock

conn = dd.connect('dagher.duckdb')


def create_clients_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients(
            id INTEGER,
            name VARCHAR,
            risk_tolerance VARCHAR,
            age INTEGER,
            cash_position FLOAT,
            goals VARCHAR,
            considerations VARCHAR
            )"""
    )
    print(f"Table: 'clients' created in dagher.duckdb")


def add_client(conn: dd.DuckDBPyConnection, client: Client) -> None:
    print(f"Adding {client.name} to clients table in dagher.duckdb")
    conn.execute(
        "INSERT INTO clients VALUES (?,?,?,?,?,?,?)",
        [client.id, client.name, client.risk_tolerance, client.age, client.cash_position, client.goals, client.considerations]
    )
    
def get_client_data(conn: dd.DuckDBPyConnection, client: Client) -> pd.DataFrame:
    result = conn.execute(
        "SELECT * FROM clients WHERE id = ?",
        [client.id]
    ).df()

    return result


s = [Stock(ticker="AMZN", shares="10", purchase_price=12.0, purchase_date=date(2024, 1, 1)),
     Stock(ticker="MSFT", shares="12", purchase_price=10, purchase_date=date(2024, 1, 1))]

c1 = Client(id=123, name="John", risk_tolerance="High", holdings=s, goals="retirement")

# create_clients_table(conn)
# add_client(conn, c1)
print(get_client_data(conn, c1).to_string())


