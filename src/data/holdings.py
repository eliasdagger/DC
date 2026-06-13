from pydantic import Field, BaseModel
from typing import List, Optional
import duckdb as dd
import pandas as pd
from datetime import date

conn = dd.connect('dagher.duckdb')


class Stock(BaseModel):
    ticker: str
    shares: float
    purchase_date: date
    purchase_price: float
    sale_date: date = Field(default = None)
    sale_price: float = Field(default = None)
    dividends: float

class Client(BaseModel):
    id: int
    name: str = Field(default = "Anon")
    risk_tolerance: str
    age: int = Field(default=None)
    holdings: List[Stock] = Field(default_factory = list, description = "Current portfolio holdings")
    holdings_value: int = Field(default = 0)
    total_holdings: int = Field(default = None)
    cash_position: int = Field(default=None)
    goals: str 
    considerations: str = Field(default=None)

def create_holdings_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS holdings(
            ticker VARCHAR,
            shares FLOAT,
            purchase_date DATE,
            purchase_price FLOAT,
            sale_date DATE,
            sale_price FLOAT,
            dividends FLOAT
        )"""
    )

def add_holdings(conn: dd.DuckDBPyConnection, stocks: List[Stock]) -> None:
    for stock in stocks:
        conn.execute(
            "INSERT INTO holdings VALUES (?,?,?,?,?,?,?)",
            [stock.ticker, stock.shares, stock.purchase_date, stock.purchase_price,
             stock.sale_date, stock.sale_price, stock.dividends]
        )
