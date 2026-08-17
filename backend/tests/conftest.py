"""Pytest defaults: demo seed on so existing tests keep using AUI sample accounts."""

import os

os.environ.setdefault("OFFICEHOURS_DEMO", "true")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")
