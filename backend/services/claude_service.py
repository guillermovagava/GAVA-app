"""
Uses the Anthropic Claude API to draft recruitment outreach emails.
"""
import os
import anthropic


def draft_email(
    business_name: str,
    contact_name: str | None,
    category: str | None,
    city: str | None,
    state: str | None,
    tone: str = "professional",
    custom_instructions: str = "",
) -> dict:
    """
    Draft a recruitment outreach email tailored to the lead.
    Returns {"subject": "...", "body": "..."} or {"error": "..."}
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set in .env"}

    client = anthropic.Anthropic(api_key=api_key)

    greeting = f"Dear {contact_name}," if contact_name else f"Dear Hiring Manager,"
    location_str = f"{city}, {state}" if city and state else (state or city or "your area")

    prompt = f"""You are writing a recruitment outreach email on behalf of GAVA Recruitment,
a staffing agency that specializes in placing seasonal workers at hotels, resorts,
amusement parks, and hospitality businesses across the United States and Canada.

Lead details:
- Business name: {business_name}
- Business type: {category or "hospitality/tourism"}
- Location: {location_str}
- Contact greeting: {greeting}
- Desired tone: {tone}
{f'- Additional instructions: {custom_instructions}' if custom_instructions else ''}

Write a concise, compelling recruitment outreach email.

Requirements:
- Start with: {greeting}
- Introduce GAVA Recruitment briefly
- Mention that we specialize in seasonal staffing for their type of business
- Highlight key benefits: pre-screened candidates, fast placement, flexible seasonal contracts
- Include a clear call to action (schedule a call or reply to learn more)
- Keep it under 200 words
- End with a professional sign-off (leave [Your Name] as placeholder)

Return ONLY a JSON object with two keys:
{{"subject": "the email subject line", "body": "the full email body"}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        return result
    except Exception as e:
        return {"error": str(e)}
