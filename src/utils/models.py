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


# ── Quant Schema ─────────────────────────────────────────────────────────────
class AltmanZScore(BaseModel):
    """The five raw ratios that feed the Altman Z-score.

    The weighted sum lives in src/mcda/screening.py, not here — this model
    only carries the inputs.
    """
    working_capital_total_assets: Optional[float] = None
    retained_earnings_total_assets: Optional[float] = None
    ebit_total_assets: Optional[float] = None
    market_cap_total_liabilities: Optional[float] = None
    sales_total_assets: Optional[float] = None


class ValuationMetrics(BaseModel):
    enterprise_value: Optional[float] = None
    enterprise_multiple: Optional[float] = None
    ev_ebitda: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    price_operating_cash_flow: Optional[float] = None
    p_fcf: Optional[float] = None
    earnings_yield: Optional[float] = None


class QualityMetrics(BaseModel):
    gpa: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    roic: Optional[float] = None
    fcf_margin: Optional[float] = None
    cash_conversion: Optional[float] = None
    total_accruals: Optional[float] = None


class HealthMetrics(BaseModel):
    altman_z_score: Optional[AltmanZScore] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_equity: Optional[float] = None
    net_debt_ebitda: Optional[float] = None
    interest_coverage: Optional[float] = None


class GrowthMetrics(BaseModel):
    revenue_growth: Optional[float] = None
    eps_growth: Optional[float] = None
    fcf_growth: Optional[float] = None
    gross_profit_growth: Optional[float] = None


class CapitalReturnMetrics(BaseModel):
    dividend_yield: Optional[float] = None
    buyback_yield: Optional[float] = None
    debt_paydown_yield: Optional[float] = None
    shareholder_yield: Optional[float] = None


class QuantFundamentalData(BaseModel):
    ticker: str
    sector: Optional[str] = None
    company_type: Optional[str] = None
    date: Optional[date] = None

    valuation: ValuationMetrics = Field(default_factory=ValuationMetrics)
    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    health: HealthMetrics = Field(default_factory=HealthMetrics)
    growth: GrowthMetrics = Field(default_factory=GrowthMetrics)
    capital_return: CapitalReturnMetrics = Field(default_factory=CapitalReturnMetrics)


# ── Qualitative Schema ───────────────────────────────────────────────────────
class QualInvestmentThesis(BaseModel):
    company_name: str
    ticker: str
    analyst: Optional[str] = None
    # date: Optional[date] = None
    company_type: str

    # 4 Pillar Scores
    leadership_score: Optional[float] = None
    industry_growth_score: Optional[float] = None
    moat_score: Optional[float] = None
    macro_score: Optional[float] = None

    # Pillar Insights
    leadership_insights: Optional[str] = None
    industry_growth_insights: Optional[str] = None
    moat_insights: Optional[str] = None
    macro_insights: Optional[str] = None

    status: Optional[str] = None
    price_target: Optional[float] = None


# ── Portfolio Schema ─────────────────────────────────────────────────────────
class Stock(BaseModel):
    ticker: str
    shares: float
    purchase_date: date
    purchase_price: float
    sale_date: Optional[date] = None
    sale_price: Optional[float] = None
    dividends: Optional[float] = None
    dividend_pct: Optional[float] = None


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
