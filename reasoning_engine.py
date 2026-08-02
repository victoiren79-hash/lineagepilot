"""
Calls Groq's API to decide whether a schema change is safe or risky for a
given downstream file, and explains why in plain English.

Requires the GROQ_API_KEY environment variable to be set:
    (in cmd, before running anything else)
    set GROQ_API_KEY=your_key_here

Run standalone to test:
    py -3.11 reasoning_engine.py
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"


def classify_change(old_column: str, new_column: str, file_path: str, file_content: str) -> dict:
    """Returns {"risk": "LOW"|"HIGH", "reasoning": "..."}"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    system_prompt = (
        "You are a data engineering assistant. You will be shown a SQL file "
        "and told that a column was renamed upstream. Decide if this file's "
        "use of that column is LOW risk or HIGH risk.\n\n"
        "HIGH risk: the column is used as a JOIN key (matches rows between "
        "tables), or inside an aggregation like SUM/COUNT/GROUP BY.\n"
        "LOW risk: the column is only selected/displayed, nothing else.\n\n"
        "Respond with ONLY valid JSON, no other text, in this exact format:\n"
        '{"risk": "LOW", "reasoning": "one short sentence explaining why"}'
    )

    user_prompt = (
        f"Column '{old_column}' was renamed to '{new_column}' in the source table.\n\n"
        f"File: {file_path}\n"
        f"Content:\n{file_content}\n\n"
        f"Classify the risk of this change for this file."
    )

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        },
    )
    resp.raise_for_status()
    raw_text = resp.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if the model added them anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Model did not return valid JSON. Raw output:\n{raw_text}")

    return result


if __name__ == "__main__":
    with open("models/stg_orders_v2.sql") as f:
        safe_content = f.read()
    with open("models/fct_revenue_v2.sql") as f:
        risky_content = f.read()

    print("Testing SAFE case (stg_orders_v2.sql):")
    result_safe = classify_change("user_id", "customer_id", "models/stg_orders_v2.sql", safe_content)
    print(f"  -> {result_safe}\n")

    print("Testing RISKY case (fct_revenue_v2.sql):")
    result_risky = classify_change("user_id", "customer_id", "models/fct_revenue_v2.sql", risky_content)
    print(f"  -> {result_risky}")
