from app.prompts import experience_plan as exp
from app.prompts import materials_suggestion as mat
from app.prompts import steps_suggestion as steps

ALLOWED_CATEGORIES_TEXT = "돌담, 감귤, 해녀, 요리, 목공"


def test_experience_plan_system_prompt_mentions_allowed_categories():
    prompt = exp.get_system_prompt()
    assert ALLOWED_CATEGORIES_TEXT in prompt
    assert "stone" in prompt and "tangerine" in prompt and "haenyeo" in prompt


def test_materials_system_prompt_mentions_allowed_categories():
    prompt = mat.get_system_prompt()
    assert ALLOWED_CATEGORIES_TEXT in prompt


def test_steps_system_prompt_mentions_allowed_categories():
    prompt = steps.get_system_prompt()
    assert ALLOWED_CATEGORIES_TEXT in prompt
