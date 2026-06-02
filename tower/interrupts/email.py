import json
import os
import re
from typing import Any

_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is None:
        import anthropic
        _CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _CLIENT


def _call_claude(prompt: str) -> Any:
    return _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )


_TEMPLATE_INSTRUCTIONS = {
    "complete": "The task is now complete. Write an email notifying the requester it is done.",
    "waiting": "You are waiting for the requester to take action or respond. Write an email chasing them.",
    "needs-info": "You need more information before you can proceed. Write an email requesting clarification.",
    "update": "Write a mid-task progress update email.",
}

_TONE_INSTRUCTIONS = {
    "formal": "Use professional, formal language.",
    "friendly": "Use warm, friendly but professional language.",
    "brief": "Be concise. 3 sentences maximum.",
}


def build_prompt(interrupt: dict[str, Any], template: str, tone: str) -> str:
    comments = "\n".join(
        f"- [{e['timestamp']}] {e.get('author', '')}: {e['text']}"
        for e in interrupt.get("activity", [])
        if e["type"] == "comment"
    )
    tags = ", ".join(interrupt.get("tags", [])) or "none"
    template_instruction = _TEMPLATE_INSTRUCTIONS.get(template, _TEMPLATE_INSTRUCTIONS["complete"])
    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["formal"])

    return f"""You are drafting a work email for Chase Ramone at Magiq Software.

Task details:
- Title: {interrupt['title']}
- Source: {interrupt['source']}
- Status: {interrupt['status']}
- Tags: {tags}
- Due date: {interrupt.get('dueDate') or 'none'}

Activity / comments:
{comments or 'No comments yet.'}

Instructions:
{template_instruction}
{tone_instruction}
Sign off as: Chase Ramone, Magiq Software.

Infer the recipient email address from the comments if possible, otherwise leave "to" blank.

Respond with ONLY valid JSON in this exact format:
{{"to": "<email or empty string>", "subject": "<subject line>", "body": "<email body>"}}"""


def generate_email_draft(
    interrupt: dict[str, Any], template: str, tone: str
) -> dict[str, Any]:
    try:
        response = _call_claude(build_prompt(interrupt, template, tone))
        raw = response.content[0].text.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError("No JSON in response")
        return json.loads(m.group())
    except Exception as e:
        return {"error": str(e), "to": "", "subject": "", "body": ""}
