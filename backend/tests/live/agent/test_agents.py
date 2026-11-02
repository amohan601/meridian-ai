from agent.agents import ProcurementSupervisor


def test_run_audit_returns_all_phase_reports_and_cfo_memo():
    supervisor = ProcurementSupervisor()
    request = (
        "Purchase order: 2 industrial servo motors from Siemens AG (Germany), "
        "total EUR 12,000, invoice rate EUR_USD 1.08, for the filling line upgrade."
    )

    result = supervisor.run_audit(request)

    assert set(result) == {"risk_result", "tax_result", "control_result", "cfo_memo"}
    for value in result.values():
        assert isinstance(value, str) and value.strip()
    assert "CFO AUDIT MEMORANDUM" in result["cfo_memo"].upper()
