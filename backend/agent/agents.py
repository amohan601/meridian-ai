from rag.llm import get_llm,extract_text
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from agent.middleware import build_agent_middleware
from logger.custom_logger import GLOBAL_LOGGER as log

from agent.prompt import (
    RISK_AGENT_PROMPT,
    TAX_AGENT_PROMPT,
    CONTROL_AGENT_PROMPT,
    SYNTHESIS_PROMPT_TEMPLATE
)
from agent.tools import(
    check_sanctions_list,
    get_vendor_credit_score,
    calculate_cross_border_tax,
    validate_fx_hedge,
    categorize_expense
)

def create_specialized_agent(agent_name, tools, system_prompt):
    """An agent = the LLM + a set of tools + a system prompt (+ middleware around the loop)."""
    log.info(f"creating agent {agent_name}")
    return create_agent(
        model=get_llm(),
        tools=tools,
        system_prompt=system_prompt,
        middleware = build_agent_middleware()
    )

class ProcurementSupervisor:
    def __init__(self):
        self.llm = get_llm()
        self.risk_agent = create_specialized_agent("risk_agent", [check_sanctions_list,get_vendor_credit_score],RISK_AGENT_PROMPT)
        self.tax_agent = create_specialized_agent("tax_agent", [calculate_cross_border_tax,validate_fx_hedge],TAX_AGENT_PROMPT)
        self.control_agent = create_specialized_agent("control_agent", [categorize_expense],CONTROL_AGENT_PROMPT)

    @staticmethod
    def _invoke_agent(agent, request: str) -> str:
        """Run one agent and return the text of its final message."""
        log.info('_invoke_agent')
        result = agent.invoke({"messages": [HumanMessage(content=request)]})
        return result["messages"][-1].text  # .text joins Gemini's content blocks
    
    def run_audit(self, request:str) -> dict: 
        log.info(f'Entered run_audit for request: {request}')
        log.info("Starting audit phase", phase="1 - Risk & Compliance")
        risk_result = self._invoke_agent(self.risk_agent,request)
        log.info("Phase complete", phase="Risk & Compliance", result=risk_result)
        
        log.info("Starting audit phase", phase="2 - Tax & Treasury")
        tax_result = self._invoke_agent(self.tax_agent,request)
        log.info("Phase complete", phase="Tax & Treasury", result=tax_result)

        log.info("Starting audit phase", phase="3 - Financial Control")
        control_result = self._invoke_agent(self.control_agent, request)
        log.info("Phase complete", phase="Financial Control", result=control_result)

        # Final synthesis by the CFO prompt (a plain LLM call, no tools)
        synthesis_prompt =SYNTHESIS_PROMPT_TEMPLATE.format(
            risk_result=risk_result,
            tax_result=tax_result,
            control_result=control_result,
        )
        log.info("Starting audit phase", phase="4 - CFO Synthesis")
        cfo_memo = extract_text(self.llm.invoke(synthesis_prompt).content)
        log.info("CFO Synthesis complete", memo=cfo_memo)
        
        return {
            "risk_result": risk_result,
            "tax_result": tax_result,
            "control_result": control_result,
            "cfo_memo": cfo_memo,
        }