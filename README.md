# 🇿🇲 Zed SNI Scanner

A Zambia-focused Telegram utility for authorized hostname/SNI connectivity diagnostics.

## Phase 1

- Telegram bot with inline buttons
- MTN Zambia, Airtel Zambia, Zamtel and ZedMobile network selection
- DNS, TCP, TLS/SNI and HTTPS testing
- Active / unstable / dead classification
- SQLite foundation
- Environment-variable configuration

## Run locally

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`.
4. Put your BotFather token in `.env`.
5. Start:

```bash
python -m bot.main
```

## Security

Never commit `.env`, Telegram bot tokens, API keys, passwords, or other secrets.

## Network-specific testing

A server-side test does not prove that a hostname works from MTN, Airtel, Zamtel, or ZedMobile. Phase 2 will add authorized network-side test agents and a results database.

## Scope

This project is intended for legitimate connectivity diagnostics and infrastructure the operator is authorized to test. It does not automate bypassing carrier billing or access controls.
