"""Tests for MVP prompt builder."""

from mvp.imggen.prompt_builder import OutfitPromptContext, PromptBuilder


def test_prompt_builder_includes_context() -> None:
    builder = PromptBuilder()
    context = OutfitPromptContext(
        description="Белая рубашка и тёмные джинсы.",
        style="casual",
        occasion="ужин",
        weather="прохладно",
    )

    garments = [
        {"label": "белая рубашка", "category": "top", "filename": "top.jpg"},
        {"label": "тёмные джинсы", "category": "bottom", "filename": "bottom.jpg"},
    ]
    prompt = builder.build(garments, context, selfie_filename="selfie.jpg")

    assert "белая рубашка" in prompt
    assert "файл selfie.jpg" in prompt
    assert "Стиль: casual" in prompt
    assert "Повод: ужин" in prompt
