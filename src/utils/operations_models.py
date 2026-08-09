"""
Module: Data Schemas/Blueprints

Problem:
Client and portfolio data needs structure and validation. Without schemas,
inconsistent data causes bugs in calculations and storage.

Description:
Defines Pydantic models for stocks, clients, quantitative fundamentals, and
qualitative investment theses. Ensures all data matches expected types and
constraints before entering the system.

Key Classes:
- Stock: Represents a single stock position
- Client: Represents a client with holdings
- QuantFundamentalData: All quantitative metrics for one company
- QualInvestmentThesis: 4-pillar qualitative judgement for one company

Dependencies:
- pydantic: For schema validation
- typing: For type hints
- datetime: For date fields

Note on Optional:
Fields that may be missing are typed `Optional[X] = None` rather than
`X = Field(default=None)`. Both behave the same at runtime, but only the
first is honest about the type, which keeps Pylance quiet.

Example:
    >>> stock = Stock(ticker="AAPL", shares=100, purchase_price=150.25, purchase_date=date(2024, 1, 15))
    >>> client = Client(client_id=1, name="John", risk_tolerance="medium", holdings=[stock], goals="Growth")
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class Client(BaseModel):
    client_id: int
    name: str = Field(default="Anon")
    risk_tolerance: str
    age: Optional[int] = None
    holdings: List[Stock] = Field(default_factory=list, description="Current portfolio holdings")
    holdings_value: int = Field(default=0)
    total_holdings: Optional[int] = None
    cash_position: Optional[int] = None
    goals: str
    considerations: Optional[str] = None
