from functools import lru_cache

from app.services.cv_parser.base import CVParser
from app.services.cv_parser.rule_based import RuleBasedCVParser


@lru_cache
def get_cv_parser() -> CVParser:
    from app.services.llm.factory import has_configured_llm_keys

    if has_configured_llm_keys():
        from app.services.cv_parser.llm import LLMCVParser
        from app.services.llm.factory import get_llm_service

        return LLMCVParser(get_llm_service())
    return RuleBasedCVParser()
