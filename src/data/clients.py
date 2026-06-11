import pandas as pd
import duckdb as dd
import numpy as np
from datetime import date
from src.utils.models import Client

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
    print(f"Clients data Available in dagher.duckdb")


def add_client(conn: dd.DuckDBPyConnection, client: Client) -> None:
    conn.execute(
        "INSERT INTO clients VALUES (?,?,?,?,?,?,?)",
        [client.id, client.name, client.risk_tolerance, client.age, client.cash_position, client.goals, client.considerations]
        )
    

create_clients_table()

