"""
Module: [Module Name]

Problem:


Description:
Implementing a universal framework for storing client data.

Key Functions:
- function_name: Brief description of what it does
- function_name: Brief description of what it does

Dependencies:
- pandas: For data manipulation
- duckdb: For database interactions

Example:
    >>> from src.data.ingestion import get_prices
    >>> prices = get_prices('AAPL', start_date='2024-01-01')
    >>> print(prices.head())
"""

from typing import List, Optional
from pydantic import BaseModel, Field
# Type hinting for code clarity
from datetime import date

class Portfolio(BaseModel):
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: date

class Client(BaseModel):
    client_id: int
    name: str = Field(default = "Anon")
    risk_tolerance: str
    age: int = Field(default=None)
    portfolio: List[Portfolio] = Field(default_factory = list, description = "Current portfolio holdings")
    total_holdings: int = Field(default = None)
    cash_position: int = Field(default=None)
    goals: str 
    considerations: str = Field(default=None)



portfolio1 = Portfolio(
    ticker="AAPL",
    shares=100,
    purchase_price=150.25,
    purchase_date=date(2024, 1, 15)
)

client1 = Client(
    client_id=1,
    name="John Doe",
    risk_tolerance="medium",
    age=35,
    portfolio=[portfolio1],
    total_holdings=1,
    cash_position=50000,
    goals="Long-term wealth accumulation",
    considerations="No sector concentration above 30%"
)

print(client1)

