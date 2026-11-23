"""Server-side access to Groq chat completions."""
import json
import os
import urllib.request


def model():
    return os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b"


def career_model():
    return os.getenv("GROQ_CAREER_MODEL") or model()


def complete(model_name, instructions, user_text, token_limit, timeout, response_format=None):
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_text},
        ],
        "max_completion_tokens": token_limit,
    }
    if response_format:
        payload["response_format"] = response_format
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + os.environ["GROQ_API_KEY"].strip(),
            "Content-Type": "application/json",
            "User-Agent": "TalentForge/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        choice = json.load(response)["choices"][0]
    if choice.get("finish_reason") != "stop" or not choice["message"].get("content"):
        raise ValueError("Incomplete Groq response")
    return choice["message"]["content"]
