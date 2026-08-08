"""
Module: Configuration

Problem:
Paths, API keys, and tunable criteria were hardcoded in whichever file needed
them. Changing a weight meant editing code.

Description:
Single source of truth for paths, environment variables, and the MCDA criteria
defined in configs/criteria.yaml.

Key Functions:
- load_criteria: Read and parse configs/criteria.yaml

Dependencies:
- python-dotenv: Load .env
- pyyaml: Parse criteria.yaml

Example:
    >>> criteria = load_criteria()
    >>> criteria['screening']['altman_z_min']
    1.81
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIGS_DIR = ROOT_DIR / "configs"
DB_PATH = os.getenv("DB_PATH", str(ROOT_DIR / "dagher.duckdb"))

# API Keys
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def load_criteria() -> dict:
    """Load the MCDA criteria (pillar weights + screening thresholds)."""
    with open(CONFIGS_DIR / "criteria.yaml", "r") as f:
        return yaml.safe_load(f)
