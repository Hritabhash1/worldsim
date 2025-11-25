# app.py
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from world import World
import os
import time
import json
import requests
import traceback

app = Flask(__name__)
app.debug = True
CORS(app)

# ---------------- PATHS ----------------
WORLD_FILE = os.path.join(os.path.dirname(__file__), "data", "world_seed.json")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

world = World(WORLD_FILE)

# ---------------- GROQ CONFIG ----------------
# PUT YOUR NEW KEY HERE (do NOT paste leaked old ones)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_TIMEOUT = 20


# ---------------- JSON EXTRACTION ----------------
def _extract_json_from_text(text: str):
    if not text:
        return None

    txt = text.strip()

    # code fences
    if txt.startswith("```"):
        parts = txt.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("{") and p.endswith("}"):
                try:
                    return json.loads(p)
                except:
                    pass

    # raw { ... }
    s = txt.find("{")
    e = txt.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(txt[s:e+1])
        except:
            pass

    # whole text fallback
    try:
        return json.loads(txt)
    except:
        return None


# ---------------- GROQ CALL ----------------
def call_groq(prompt: str):
    """
    Returns (parsed_json or None, debug_info).
    Groq is OpenAI-compatible.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 200
    }

    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=GROQ_TIMEOUT)
        r.raise_for_status()
        raw = r.json()

        text = raw["choices"][0]["message"]["content"]

        parsed = _extract_json_from_text(text)
        return parsed, {"raw": raw, "text": text}

    except Exception as e:
        return None, {"error": str(e), "trace": traceback.format_exc()}


# ---------------- BASIC ROUTES ----------------
@app.route("/api/agents")
def get_agents():
    return jsonify([a.to_dict() for a in world.agents])


@app.route("/api/world")
def get_world():
    return jsonify({
        "agents": [a.to_dict() for a in world.agents],
        "pois": world.pois
    })


# ---------------- TICK (NO LLM) ----------------
@app.route("/api/tick", methods=["POST"])
def tick():
    steps = int((request.json or {}).get("steps", 1))
    for _ in range(steps):
        world.step()
    return jsonify({"status": "ok", "agents": [a.to_dict() for a in world.agents]})


# ---------------- STATS ----------------
@app.route("/api/stats")
def get_stats():
    last = request.args.get("last")
    try:
        last = int(last) if last else None
    except:
        last = None
    return jsonify({"stats": world.get_stats(last)})


@app.route("/api/export_stats")
def export_stats():
    f = world.export_stats_csv()
    return send_file(f, as_attachment=True)


# ---------------- RUN SIM ----------------
@app.route("/api/run_sim", methods=["POST"])
def run_sim():
    body = request.json or {}
    ticks = int(body.get("ticks", 240))
    reset = bool(body.get("reset_seed", True))

    if reset:
        world.load_seed(WORLD_FILE)

    for _ in range(ticks):
        world.step()

    return send_file(world.export_stats_csv(), as_attachment=True)


# ---------------- SINGLE-AGENT THINK (LLM) ----------------
@app.route("/api/agent_llm", methods=["POST"])
def agent_llm():
    body = request.json or {}
    agent_id = body.get("agent_id")

    if not agent_id:
        return jsonify({"error": "agent_id required"}), 400

    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    prompt = f"""
You are an AI agent inside a 2D grid simulation.
Return ONLY strict JSON, exactly like:

{{
  "thought": "short reasoning",
  "action": "move",
  "dx": 1,
  "dy": 0,
  "memory": "short memory"
}}

Rules:
- action must be "move" or "idle".
- dx, dy must be integers in [-1, 0, 1].

State:
id: {agent.id}
type: {agent.type}
position: ({agent.x}, {agent.y})
goals: {agent.goals}
recent_memory: {agent.memory[-5:]}
pois: {world.pois}
"""

    parsed, debug = call_groq(prompt)

    if not parsed:
        fallback = {
            "thought": "LLM failed",
            "action": "idle",
            "dx": 0,
            "dy": 0,
            "memory": str(debug)
        }
        return jsonify({"agent_id": agent_id, "llm_result": fallback, "debug": debug}), 502

    # save memory
    if parsed.get("memory"):
        agent.add_memory(parsed["memory"], source="llm")

    return jsonify({"agent_id": agent_id, "llm_result": parsed, "debug": debug})


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    print("🔥 Groq backend running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
