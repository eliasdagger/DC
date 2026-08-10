from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class Company(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    company_type: str

# ── Quant Schema ─────────────────────────────────────────────────────────────
class AltmanZScore(BaseModel):
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
    # sector / company_type deliberately absent — join to Company on ticker.
    ticker: str
    fiscal_period_end: date
    filing_available_date: date

    valuation: ValuationMetrics = Field(default_factory=ValuationMetrics)
    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    health: HealthMetrics = Field(default_factory=HealthMetrics)
    growth: GrowthMetrics = Field(default_factory=GrowthMetrics)
    capital_return: CapitalReturnMetrics = Field(default_factory=CapitalReturnMetrics)

class FundamentalsRaw(BaseModel):
    ticker: str
    fiscal_period_end: date
    filing_available_date: date
    revenue: float
    cogs: float
    gross_profit: float
    ebit: float
    ebitda: float
    net_income: float
    cfo: float
    capex: float
    total_assets: float
    total_liabilities: float
    current_assets: float
    current_liabilities: float
    retained_earnings: float
    cash: float
    total_debt: float
    preferred_equity: float
    shares_outstanding: float
    dividends_paid: float
    buybacks: float
    debt_repaid: float
    interest_expense: float


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
