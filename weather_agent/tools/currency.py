import httpx
from langchain_core.tools import tool

FAILURE_MARKERS = ("Currency conversion failed",)


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert money between currencies. Args: amount, from_currency e.g. 'USD', to_currency e.g. 'EUR'."""
    res = httpx.get(
        "https://api.frankfurter.dev/v1/latest",
        params={"base": from_currency.upper(), "symbols": to_currency.upper()},
        timeout=10,
    ).json()
    if "rates" not in res:
        return f"Currency conversion failed: {res.get('message', res)}"
    rate = res["rates"][to_currency.upper()]
    return f"{amount} {from_currency.upper()} = {amount * rate:.2f} {to_currency.upper()} (rate {rate}, {res['date']})"
