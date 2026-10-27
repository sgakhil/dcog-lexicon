"""Minimal client for a local Ollama server (https://ollama.com).

Uses only the Python standard library. The model runs on your own machine,
so fieldnotes never leave it.
"""
import json
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("DCOG_MODEL", "qwen2.5:7b")


class LLMError(RuntimeError):
    pass


def chat(messages, model=DEFAULT_MODEL, schema=None, temperature=0.0, seed=42, timeout=900):
    """Send a chat request. If `schema` is given, output is constrained to that JSON schema."""
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "seed": seed, "num_ctx": 16384},
    }
    if schema is not None:
        body["format"] = schema
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise LLMError(
            f"Could not reach Ollama at {OLLAMA_URL} ({e.reason}).\n"
            "Is it installed and running? Try:  ollama serve   (or check: ollama list)") from e
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")
        if "not found" in msg:
            raise LLMError(f"Model '{model}' is not downloaded. Run:  ollama pull {model}") from e
        raise LLMError(f"Ollama error {e.code}: {msg}") from e
    return data["message"]["content"], {
        "model": data.get("model", model),
        "eval_count": data.get("eval_count"),
        "total_duration_s": round((data.get("total_duration") or 0) / 1e9, 1),
    }


def model_digest(model=DEFAULT_MODEL):
    """Exact model version (digest), recorded for reproducibility."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as resp:
            for m in json.loads(resp.read()).get("models", []):
                if m.get("name") == model or m.get("model") == model:
                    return m.get("digest")
    except Exception:
        pass
    return None
