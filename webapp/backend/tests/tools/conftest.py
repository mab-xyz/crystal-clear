"""Minimal env setup so backfill_first_time_interactions_core can be imported in tests."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CACHE_URL", "redis://localhost:6379")
os.environ.setdefault("ALLIUM_API_KEY", "test-key")
os.environ.setdefault("ETHERSCAN_API_KEY", "test-key")
os.environ.setdefault("ETH_NODE_URL", "http://localhost:8545")
os.environ.setdefault("ETH_NODE_URLS", "http://localhost:8545")
