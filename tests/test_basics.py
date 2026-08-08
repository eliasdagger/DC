"""
Simple beginner testingr.

Covers:
1. Creating objects (Stock, Client)
2. Pulling data (yfinance)
3. DuckDB (saving + reading data)
4. Calculations (returns, volatility)
"""
from datetime import date

import duckdb as dd
import pandas as pd
import pytest
from pydantic import ValidationError

from src.utils.models import Stock, Client
from src.data.ingestion import get_prices, cache_prices, get_cached_price
from src.data.clients import create_clients_table, add_client, get_client_data
from src.data.holdings import create_holdings_table, add_holdings, get_holdings
from src.features.returns import simple_returns, volatility, cumulative_returns
