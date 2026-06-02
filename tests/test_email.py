import pytest
from unittest.mock import patch, MagicMock
from tower.interrupts.email import build_prompt, generate_email_draft

SAMPLE_INTERRUPT = {
    "id": "test-1",
    "title": "Fix NATA export",
    "source": "Support",
    "dueDate": "2026-06-01",
    "priority": "urgent",
    "status": "in-progress",
    "tags": ["waiting-for-feedback"],
    "activity": [
        {"type": "comment", "author": "Chase",
         "text": "Fix deployed. Waiting for NATA to confirm.",
         "timestamp": "2026-06-01T08:00:00Z"}
    ],
}


def test_build_prompt_contains_title():
    prompt = build_prompt(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "Fix NATA export" in prompt


def test_build_prompt_contains_template():
    prompt = build_prompt(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "complete" in prompt.lower() or "resolved" in prompt.lower()


def test_build_prompt_contains_comment():
    prompt = build_prompt(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "Fix deployed" in prompt


def test_generate_email_draft_structure():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"to": "x@y.com", "subject": "Done", "body": "Hi"}')]
    with patch("tower.interrupts.email._call_claude", return_value=mock_response):
        result = generate_email_draft(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert result["to"] == "x@y.com"
    assert result["subject"] == "Done"
    assert result["body"] == "Hi"


def test_generate_email_draft_api_failure():
    with patch("tower.interrupts.email._call_claude", side_effect=Exception("API error")):
        result = generate_email_draft(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "error" in result
