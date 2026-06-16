"""
Module: Stock Schema Database Storage

Problem:
In order to access data, the data must be stored within a trackable, structured database.
Below, data is received then written in a local file.
Description:
Operations include: creating named tables, while ensuring no redundencies, and allocating 
essential Stock data in a ordered manner.  

Key Functions:
- create_holdings_table: Creates a table of client's stocks and their respective information (ticker, price).
- add_client: Fills in client data into 'holdings' table

Dependencies:
- duckdb: Store and query data locally

Example:
    >>> stocks = [
                    Stock(ticker="AMZN", shares=10, purchase_date=date(2024, 1, 1), purchase_price=120.0, dividends=0.0),
                    Stock(ticker="MSFT", shares=12, purchase_date=date(2024, 1, 1), purchase_price=310.0, dividends=2.5),
                ]
"""
from typing import List
import duckdb as dd
from datetime import date
from src.utils.models import Stock

conn = dd.connect('dagher.duckdb')

def create_holdings_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS holdings(
            ticker VARCHAR,
            shares FLOAT,
            purchase_date DATE,
            purchase_price FLOAT,
            sale_date DATE,
            sale_price FLOAT,
            dividends FLOAT, 
            dividend_pct FLOAT
        )"""
    )

def add_holdings(conn: dd.DuckDBPyConnection, stocks: List[Stock]) -> None:
    print(f"Adding: {stocks} to dagher.duckdb table - holdings")
    for stock in stocks:
        conn.execute(
            "INSERT INTO holdings VALUES (?,?,?,?,?,?,?, ?)",
            [stock.ticker, stock.shares,
             stock.purchase_date, stock.purchase_price,
             stock.sale_date, stock.sale_price,
             stock.dividends, stock.dividend_pct]
        )

def get_holdings(conn: dd.DuckDBPyConnection, client_id: int) -> pd.DataFrame:
    holdings = conn.execute(
        "SELECT * FROM holdings WHERE id = ?",
        [client_id]
    ).df()





# create_holdings_table(conn)
# add_holdings(conn, stocks)
# print(conn.execute("SELECT * FROM holdings").df().to_string())

