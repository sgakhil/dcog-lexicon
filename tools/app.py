"""Local browser app: paste a fieldnote, get a draft activity map, correct it, save it.

    python3 app.py            # opens http://localhost:8765 in your browser
    python3 app.py --port 9000 --no-browser

The app runs only on this computer (it listens on 127.0.0.1, not the network).
Notes are saved to ../notes/ and maps to ../predicted/; both folders are kept
out of git. The model is the local one served by Ollama.
"""
import argparse
import json
import re
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from compare import score
from extract import extract
from lexicon import DEFAULT_DOMAIN, ROOT, domain, domain_names, load, notes, validate
from llm import DEFAULT_MODEL, OLLAMA_URL

NOTES, PRED = ROOT / "notes", ROOT / "predicted"
PAGE = Path(__file__).with_name("app.html")
MAPDRAW = ROOT / "site" / "mapdraw.js"


def safe_name(s):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (s or "").strip())[:60].strip("_")
    return s or "note"


def ollama_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])], None
    except Exception as e:
        return [], str(e)


def map_library():
    out = []
    for folder, kind in ((PRED, "saved"), (ROOT / "gold", "hand-coded"), (ROOT / "examples", "example")):
        for p in sorted(folder.glob("*.json")) if folder.exists() else []:
            try:
                d = load(p)
                if "nodes" in d:
                    out.append({"path": str(p.relative_to(ROOT)), "title": d.get("title", p.stem), "kind": kind,
                                "domain": d.get("domain", DEFAULT_DOMAIN)})
            except Exception:
                pass
    return out


def check(d):
    try:
        return validate(d), (notes(d) if not validate(d) else [])
    except Exception as e:
        return [f"could not check: {e}"], []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, PAGE.read_text(), "text/html")
        if path == "/mapdraw.js":
            return self._send(200, MAPDRAW.read_text(), "text/javascript")
        if path == "/api/info":
            models, err = ollama_models()
            names = domain_names()
            return self._send(200, {
                "domains": {n: domain(n) for n in names},
                "examples": {n: (ROOT / domain(n)["example"]["note"]).read_text() for n in names},
                "models": models, "ollama_error": err, "default_model": DEFAULT_MODEL,
                "library": map_library()})
        if path == "/api/map":
            rel = self.path.split("path=", 1)[-1]
            p = (ROOT / urllib.request.url2pathname(rel)).resolve()
            if ROOT not in p.parents or p.suffix != ".json" or not p.exists():
                return self._send(404, {"error": "not found"})
            return self._send(200, load(p))
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            req = self._body()
        except Exception:
            return self._send(400, {"error": "bad request"})
        if path == "/api/extract":
            note = (req.get("note") or "").strip()
            if not note:
                return self._send(400, {"error": "The note is empty."})
            dom = req.get("domain") if req.get("domain") in domain_names() else DEFAULT_DOMAIN
            name = safe_name(req.get("name"))
            NOTES.mkdir(exist_ok=True)
            note_path = NOTES / f"{name}.txt"
            note_path.write_text(note + "\n")
            try:
                d, errors, log = extract(note_path, req.get("model") or DEFAULT_MODEL, dom=dom)
            except Exception as e:
                return self._send(502, {"error": str(e)})
            if d is None:
                return self._send(200, {"map": None, "errors": errors, "notes": [], "log": log})
            d.setdefault("id", name)
            d["domain"] = dom
            errs, nts = check(d)
            return self._send(200, {"map": d, "errors": errs, "notes": nts, "log": log})
        if path == "/api/check":
            d = req.get("map")
            if not isinstance(d, dict):
                return self._send(200, {"errors": ["The text is not a JSON object."], "notes": []})
            errs, nts = check(d)
            return self._send(200, {"errors": errs, "notes": nts})
        if path == "/api/save":
            d, name = req.get("map"), safe_name(req.get("name"))
            if not isinstance(d, dict):
                return self._send(400, {"error": "Nothing to save."})
            PRED.mkdir(exist_ok=True)
            out = PRED / f"{name}.json"
            out.write_text(json.dumps(d, indent=2, ensure_ascii=False))
            return self._send(200, {"saved": str(out.relative_to(ROOT)), "library": map_library()})
        if path == "/api/compare":
            ref = (ROOT / req.get("ref", "")).resolve()
            if ROOT not in ref.parents or not ref.exists():
                return self._send(404, {"error": "Hand-coded map not found."})
            try:
                s = score(load(ref), req.get("map"))
            except Exception as e:
                return self._send(200, {"error": f"Could not compare: {e}"})
            return self._send(200, {"scores": s})
        self._send(404, {"error": "not found"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"dcog-lexicon app running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
