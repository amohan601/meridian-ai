from agent.prompt import RISK_AGENT_PROMPT, SYNTHESIS_PROMPT_TEMPLATE


def test_synthesis_prompt_formats_and_keeps_alert_keywords():
    memo_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        risk_result="RED ALERT: test",
        tax_result="FX SUCCESS",
        control_result="APPROVED",
    )

    assert "RED ALERT: test" in memo_prompt
    assert "FX SUCCESS" in memo_prompt
    assert "APPROVED" in memo_prompt
    # The CFO decision rules rely on these literal strings appearing in the specialist prompts.
    assert "RED ALERT" in RISK_AGENT_PROMPT
