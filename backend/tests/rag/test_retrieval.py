from rag.retrieval import ask_question


def test_ask_question_answers_from_indexed_documents(indexed_documents):
    answer = ask_question("What does the Aldermoor procurement policy say about approval thresholds?")

    assert answer.strip()
