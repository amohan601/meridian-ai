from rag.llm import extract_text, get_llm


def test_get_llm_answers_a_real_prompt():
    response = get_llm().invoke("Reply with the single word: pong")

    assert extract_text(response.content).strip()
