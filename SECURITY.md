# Security Policy

## Supported Versions
Only the latest main branch is supported with security updates.

## Reporting a Vulnerability
Do NOT open a public issue for security bugs. Email the maintainer
or use GitHub private vulnerability reporting if enabled.

Include: description, impact, reproduction steps, affected commit,
and suggested fix if any. You will get a response within 7 days.

## Secrets
Never commit .env, passwords, API keys, or dumps. .env is gitignored.
Rotate SECRET_KEY, MYSQL_PASSWORD, and GOOGLE_MAPS_API_KEY if exposed.
Demo credentials in README/database.sql must be changed before deploy.
