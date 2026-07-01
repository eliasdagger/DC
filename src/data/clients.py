"""
Module: Client Schema Database Storage

Problem:
In order to access data, the data must be stored within a trackable, structured database.
Below, data is received then written in a local file.
Description:
Operations include: creating named tables, ensuring no redundencies, allocating 
essential Client data in a ordered manner, and retrieving desired information.  

Key Functions:
- create_clients_table: Creates a table of clients and their respective information.
- add_client: Fills in client data into 'clients' table
- get_client_data: Retrieves client data

Dependencies:
- pandas: Efficiently return the table via .df() method 
- duckdb: Store and query data locally

Example:
    >>> c1 = Client(id=123, name="John", risk_tolerance="High", holdings=List[Stock], goals="retirement")
"""

import pandas as pd
import duckdb as dd
from src.utils.models import Client

# from src.utils.models import Client, Stock

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
        [client.client_id, client.name, 
         client.risk_tolerance, client.age, 
         client.cash_position, client.goals, 
         client.considerations]
    )
    
def get_client_data(conn: dd.DuckDBPyConnection, client: Client) -> pd.DataFrame:
    result = conn.execute(
        "SELECT * FROM clients WHERE id = ?",
        [client.client_id]
    ).df()

    return result




