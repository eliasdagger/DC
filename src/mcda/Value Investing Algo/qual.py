"""
Module: Qualitative Thesis Storage

Problem:
The 4-pillar qualitative judgement on a company (leadership, industry growth,
moat, macro) lives in an analyst's head. To score it against the quant side it
has to be written down in a structured, queryable form.

Description:
Stores and retrieves QualInvestmentThesis records in the 'theses' DuckDB table.
Storage only — the weighting and scoring of these pillars lives in scoring.py.

Key Functions:
- create_theses_table: Initialize the 'qualitative_theses' table
- cache_analysis: Write one thesis to the table
- get_thesis: Retrieve stored theses for a ticker

Dependencies:
- duckdb: Store and query data locally
- pandas: Return results as a DataFrame

Example:
    >>> thesis = QualInvestmentThesis(company_name="Amazon", ticker="AMZN",
    ...                               company_type="High-Growth", moat_score=8.5)
    >>> create_theses_table(conn)
    >>> cache_analysis(conn, thesis)
    >>> get_thesis(conn, "AMZN")
"""

import pandas as pd
import duckdb as dd

from src.utils.models import QualInvestmentThesis


def create_theses_table(conn: dd.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qualitative_theses(
            company_name VARCHAR,
            ticker VARCHAR,
            analyst VARCHAR,
            date DATE,
            company_type VARCHAR,

            leadership_score FLOAT,
            industry_growth_score FLOAT, 
            moat_score FLOAT,
            macro_score FLOAT, 

            leadership_insights VARCHAR,
            industry_growth_insights VARCHAR,
            moat_insights VARCHAR, 
            macro_insights VARCHAR,

            status VARCHAR,
            price_target FLOAT)
    """)
    
    print("Table: 'theses' created in dagher.duckdb")


def cache_analysis(conn: dd.DuckDBPyConnection, company_thesis: QualInvestmentThesis) -> None:
    print(f"Adding {company_thesis.ticker} thesis to theses table in dagher.duckdb")
    conn.execute(
        "INSERT INTO qualitative_theses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [company_thesis.company_name, company_thesis.ticker, company_thesis.analyst, company_thesis.date, company_thesis.company_type,
         company_thesis.leadership_score, company_thesis.industry_growth_score, company_thesis.moat_score, company_thesis.macro_score, company_thesis.leadership_insights, 
         company_thesis.industry_growth_insights, company_thesis.moat_insights, company_thesis.macro_insights, company_thesis.status, company_thesis.price_target]
    )
    

def get_thesis(conn: dd.DuckDBPyConnection, ticker: str) -> pd.DataFrame:
    res = conn.execute(
        "SELECT * FROM qualitative_theses WHERE ticker = ? ORDER BY date DESC LIMIT 1",
        [ticker]
    ).df()
    
    return res
    
