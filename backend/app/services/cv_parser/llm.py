import json
import logging

from pydantic import ValidationError

from app.prompts.cv_extraction import build_cv_extraction_prompt
from app.services.cv_parser.base import CVParser, ParsedCV
from app.services.cv_parser.rule_based import RuleBasedCVParser
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class LLMCVParser(CVParser):
    """LLM-backed CV parser. Falls back to the rule-based parser if the LLM
    is unavailable or keeps returning invalid JSON, so a flaky/unreachable
    provider never breaks the upload pipeline."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service
        self._fallback = RuleBasedCVParser()

    def parse(self, raw_text: str) -> ParsedCV:
        system_prompt, user_prompt = build_cv_extraction_prompt(raw_text)
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                raw_response = self._llm.complete(system_prompt, user_prompt)
                data = json.loads(_strip_code_fences(raw_response))
                return ParsedCV.model_validate(data)
            except (json.JSONDecodeError, ValidationError, Exception) as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("LLM CV parse attempt %s/%s failed: %s", attempt, MAX_RETRIES + 1, exc)
        logger.error("LLM CV parsing failed after retries, falling back to rule-based parser", exc_info=last_error)
        return self._fallback.parse(raw_text)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
