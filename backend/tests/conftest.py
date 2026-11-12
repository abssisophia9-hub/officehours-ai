"""Pytest defaults: demo seed on so existing tests keep using AUI sample accounts."""

import os

os.environ.setdefault("OFFICEHOURS_DEMO", "true")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")
os.environ.setdefault("OFFICEHOURS_RATE_LIMIT", "false")
# Keep unit tests on the local Canvas mirror unless a test sets live creds.
os.environ.pop("CANVAS_BASE_URL", None)
os.environ.pop("CANVAS_API_TOKEN", None)
os.environ.pop("CANVAS_ACCESS_TOKEN", None)
