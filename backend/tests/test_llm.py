def test_get_llm_client_deepseek():
    from backend.llm import get_llm_client
    from backend.llm.deepseek import DeepSeekClient
    import os
    os.environ["LLM_PROVIDER"] = "deepseek"
    os.environ["LLM_API_KEY"] = "sk-test"
    client = get_llm_client()
    assert isinstance(client, DeepSeekClient)
    assert client.model == "deepseek-chat"
