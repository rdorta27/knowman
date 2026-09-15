from knowman.llm.base import build_prompt, current_prompt_version
from knowman.retrieval import Citation


def test_build_prompt_renders_the_versioned_template():
    citations = [Citation("a.md", 1, 2, "some fact", 0.1)]
    prompt = build_prompt("why?", citations, version="ask_v1")
    assert "why?" in prompt
    assert "a.md:L1-L2" in prompt
    assert "some fact" in prompt


def test_current_prompt_version_matches_the_default_setting():
    assert current_prompt_version() == "ask_v1"
