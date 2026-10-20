#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
if [ ! -e .env ]; then cp .env.example .env; echo 'Edit .env to enable staff dashboard.'; fi
.venv/bin/python run_local.py
