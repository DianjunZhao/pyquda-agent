"""Prompt helpers for optional LLM-assisted generation."""

from __future__ import annotations

from pyquda_agent.models import ContextBundle
from pyquda_agent.tasks.schema import Pion2ptTask


def build_generation_system_prompt() -> str:
    return (
        "You generate PyQUDA Python scripts. Preserve PyQUDA naming conventions, "
        "keep the output concrete, and do not invent unavailable physical inputs."
    )


def build_generation_user_prompt(task: Pion2ptTask, context: ContextBundle, template_code: str) -> str:
    snippet_block = "\n\n".join(
        f"Source: {snippet.path}\nSummary: {snippet.summary}\nExcerpt:\n{snippet.excerpt}"
        for snippet in context.snippets
    )
    return (
        f"Task:\n{task.to_dict()}\n\n"
        f"Repository summary:\n{context.index_summary}\n\n"
        f"Reference snippets:\n{snippet_block}\n\n"
        "Refine the following template without changing its overall structure or adding assumptions "
        "that are not supported by the task fields.\n\n"
        f"{template_code}"
    )
