import pytest
from prompts.prompt_templates import PROMPT_MAP

def test_prompt_registry():
    for name,fn in PROMPT_MAP.items():
        prompt=fn("sample title","sample bullets",[{"item_name":"demo","bullet_points":"text","gold":{"brand":"x"}}]) if name=="few_shot" else fn("sample title","sample bullets")
        assert "JSON" in prompt

def test_few_shot_requires_examples():
    with pytest.raises(ValueError): PROMPT_MAP["few_shot"]("title","bullets",[])
