"""
Module: Data Models

Problem:
Client and portfolio data needs structure and validation. Without schemas,
inconsistent data causes bugs in calculations and storage.

Description:
Defines Pydantic models for stocks and clients. Ensures all data matches
expected types and constraints before entering the system.

Key Classes:
- Stock: Represents a single stock position
- Client: Represents a client with holdings

Dependencies:
- pydantic: For schema validation
- typing: For type hints
- datetime: For date fields

Example:
    >>> stock = Stock(ticker="AAPL", shares=100, purchase_price=150.25, purchase_date=date(2024, 1, 15))
    >>> client = Client(client_id=1, name="John", risk_tolerance="medium", holdings=[stock], goals="Growth")
"""

from typing import List, Optional
from pydantic import BaseModel, Field
# Type hinting for code clarity
from datetime import date


class Stock(BaseModel):
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: date

class Client(BaseModel):
    client_id: int
    name: str = Field(default = "Anon")
    risk_tolerance: str
    age: int = Field(default=None)
    holdings: List[Stock] = Field(default_factory = list, description = "Current portfolio holdings")
    holdings_value: int = Field(default = 0)
    total_holdings: int = Field(default = None)
    cash_position: int = Field(default=None)
    goals: str 
    considerations: str = Field(default=None)