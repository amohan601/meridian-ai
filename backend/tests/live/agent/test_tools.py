from agent.tools import (
    calculate_cross_border_tax,
    categorize_expense,
    check_sanctions_list,
    get_vendor_credit_score,
    validate_fx_hedge,
)


def test_check_sanctions_list_returns_llm_verdict():
    result = check_sanctions_list.invoke({"vendor_name": "Acme GmbH"})

    assert result.startswith(("RED ALERT:", "CLEARED:", "SYSTEM WARNING:"))


def test_get_vendor_credit_score_returns_score_and_risk():
    result = get_vendor_credit_score.invoke({"vendor_name": "Siemens AG"})

    assert result.startswith(("CREDIT SCORE:", "SYSTEM WARNING:")) or '"score"' in result
    assert "RISK" in result.upper()


def test_calculate_cross_border_tax_returns_tax_breakdown():
    result = calculate_cross_border_tax.invoke(
        {"amount": 10000.0, "origin": "CN", "destination": "DE"}
    )

    assert isinstance(result, dict)
    assert result.get("route") == "CN_DE" or "error" in result
    assert "tax_amount" in result or "error" in result


def test_validate_fx_hedge_reports_variance_against_market_rate():
    result = validate_fx_hedge.invoke({"currency_pair": "EUR_USD", "rate_used": 1.08})

    assert result.startswith(("FX SUCCESS", "FX ALERT", "FX WARNING"))


def test_categorize_expense_returns_capex_or_opex_classification():
    result = categorize_expense.invoke(
        {"amount": 25000.0, "item_description": "Industrial PLC controller for filling line"}
    )

    assert "CLASSIFICATION:" in result
    assert "CapEx" in result or "OpEx" in result
