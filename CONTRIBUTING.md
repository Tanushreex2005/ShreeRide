# Contributing to ShreeRide

Thanks for your interest. This repo is currently Private.

## Workflow
1. Fork or branch from main: git checkout -b feature/short-name
2. Create venv, pip install -r requirements.txt, copy .env.example to .env
3. Make small focused commits with clear messages
4. Run smoke test: python -m py_compile app.py and python app.py
5. Open PR to main with what/why/screenshots + test steps

## Standards
- Python 3.10+, Flask 3.1 style, no secrets in code or commits
- Validate all user input server-side, hash passwords, never log .env
- Keep database.sql as single source of truth for fresh installs
- Update README if routes, env vars, or setup change

## Reporting issues
Use GitHub Issues with steps to reproduce, expected vs actual,
Python/MySQL versions, and relevant logs (redact passwords/keys).
