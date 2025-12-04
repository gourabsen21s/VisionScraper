from reasoner.reasoner import Reasoner

def test_plan_parsing(monkeypatch):
    class DummyResp:
        content = '{"action":"click","target":{"by":"id","value":"search-button"},"value":null,"confidence":0.9,"reason":"Click search"}'
    
    class MockLLM:
        def __call__(self, messages):
            return DummyResp()

    r = Reasoner(model=MockLLM())
    el = [{"id":"search-button","bbox":[1,2,3,4],"text":"Search","type":"button"}]
    action = r.plan_one("Click search", el)
    assert action.action == "click"
