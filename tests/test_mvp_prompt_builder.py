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

    prompt = builder.build(["рубашка", "джинсы"], context)

    assert "рубашка" in prompt
    assert "Стиль: casual" in prompt
    assert "Повод: ужин" in prompt
