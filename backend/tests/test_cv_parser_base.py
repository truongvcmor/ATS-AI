"""ParsedCV (and friends) are the canonical shape produced by *both*
RuleBasedCVParser and LLMCVParser before anything is written to the DB.
Real-world CVs routinely put a whole paragraph where a short field is
expected — this crashed the entire upload with a Postgres
StringDataRightTruncation error (a misclassified section produced a
400+ char "certification name" against a VARCHAR(255) column). Truncating
here, once, protects every VARCHAR-backed field regardless of parser.
"""

import pytest
from pydantic import ValidationError

from app.services.cv_parser.base import ParsedCertification, ParsedCV, ParsedLanguage


def test_certification_name_over_255_chars_is_truncated_not_rejected():
    long_name = "A" * 400
    cert = ParsedCertification(name=long_name)
    assert len(cert.name) == 255
    assert cert.name.endswith("…")


def test_certification_issuer_none_is_left_alone():
    cert = ParsedCertification(name="AWS Certified", issuer=None)
    assert cert.issuer is None


def test_language_name_over_100_chars_is_truncated():
    lang = ParsedLanguage(name="B" * 200)
    assert len(lang.name) == 100


def test_parsed_cv_full_name_and_location_are_bounded():
    parsed = ParsedCV(full_name="C" * 500, location="D" * 500, current_title="E" * 500, phone="1" * 200)
    assert len(parsed.full_name) == 255
    assert len(parsed.location) == 255
    assert len(parsed.current_title) == 255
    assert len(parsed.phone) == 50


def test_skills_list_entries_are_each_bounded():
    parsed = ParsedCV(skills=["Python", "F" * 300])
    assert parsed.skills[0] == "Python"
    assert len(parsed.skills[1]) == 150


def test_short_values_pass_through_unchanged():
    cert = ParsedCertification(name="AWS Certified Solutions Architect", issuer="Amazon")
    assert cert.name == "AWS Certified Solutions Architect"
    assert cert.issuer == "Amazon"
