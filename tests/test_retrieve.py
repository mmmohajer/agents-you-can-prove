from agent.retrieve import retrieve


def test_refund_question_hits_policy() -> None:
    chunks = retrieve("How long do I have to return a defective Standard purchase?", k=3)
    joined = " ".join(chunk.text for chunk in chunks).lower()
    assert "fourteen" in joined
    assert any(chunk.source == "policy.txt" for chunk in chunks)


def test_error_code_hits_faq() -> None:
    chunks = retrieve("What does E-4471 mean?", k=3)
    joined = " ".join(chunk.text for chunk in chunks)
    assert "E-4471" in joined
