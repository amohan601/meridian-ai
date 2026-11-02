from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    PIIMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)

from agent.middleware import build_agent_middleware, log_tool_calls


def test_build_agent_middleware_returns_stack_in_order():
    stack = build_agent_middleware()

    assert [type(m) for m in stack[:7]] == [
        PIIMiddleware,
        PIIMiddleware,
        ModelCallLimitMiddleware,
        ToolCallLimitMiddleware,
        ModelRetryMiddleware,
        ToolRetryMiddleware,
        type(log_tool_calls),
    ]
    assert stack[-1] is log_tool_calls
