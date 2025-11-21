from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from world import World
import os
import threading
import time

app = Flask(__name__)
CORS(app)

WORLD_FILE = os.path.join(os.path.dirname(__file__), "data", "world_seed.json")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)  # ensure data dir exists

world = World(WORLD_FILE)

@app.route("/api/agents", methods=["GET"])
def get_agents():
    return jsonify([a.to_dict() for a in world.agents])

@app.route("/api/world", methods=["GET"])
def get_world():
    return jsonify({
        "agents": [a.to_dict() for a in world.agents],
        "pois": world.pois
    })

@app.route("/api/tick", methods=["POST"])
def tick():
    steps = int(request.json.get("steps", 1)) if request.json else 1
    for _ in range(steps):
        world.step()
    return jsonify({"status":"ok", "agents":[a.to_dict() for a in world.agents]})

@app.route("/api/stats", methods=["GET"])
def get_stats():
    last = request.args.get("last", None)
    if last:
        try:
            last = int(last)
        except:
            last = None
    stats = world.get_stats(last_n=last)
    return jsonify({"stats": stats})

@app.route("/api/export_stats", methods=["GET"])
def export_stats():
    # ensure data dir exists
    os.makedirs(DATA_DIR, exist_ok=True)
    out_file = world.export_stats_csv()
    try:
        return send_file(out_file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e), "path": out_file}), 500

# Existing endpoint: run a simulation on server and return CSV file
@app.route("/api/run_sim", methods=["POST"])
def run_sim():
    """
    Run the world for N ticks (server-side), export stats CSV and return it.
    Request JSON:
      { "ticks": 240, "reset_seed": true }
    """
    body = request.json or {}
    ticks = int(body.get("ticks", 240))
    reset_seed = bool(body.get("reset_seed", True))

    MAX_TICKS = 200000
    if ticks < 1 or ticks > MAX_TICKS:
        return jsonify({"error": f"ticks must be between 1 and {MAX_TICKS}"}), 400

    if reset_seed:
        try:
            world.load_seed(WORLD_FILE)
        except Exception as e:
            return jsonify({"error": f"Failed to reload seed: {e}"}), 500

    try:
        for _ in range(ticks):
            world.step()
    except Exception as e:
        return jsonify({"error": f"Error during simulation: {e}"}), 500

    try:
        # ensure data dir exists before export
        os.makedirs(DATA_DIR, exist_ok=True)
        out_file = world.export_stats_csv()
        return send_file(out_file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Export failed: {e}"}), 500

# NEW endpoint: run simulation and return stats JSON (no file)
@app.route("/api/run_sim_json", methods=["POST"])
def run_sim_json():
    """
    Run the world for N ticks (server-side) and return JSON stats (no CSV).
    Request JSON:
      { "ticks": 240, "reset_seed": true, "last": 10 }
    Response JSON:
      { "stats": [...], "ticks_run": N }
    'last' optional: return only last N tick records in stats.
    """
    body = request.json or {}
    ticks = int(body.get("ticks", 240))
    reset_seed = bool(body.get("reset_seed", True))
    last = body.get("last", None)
    if last is not None:
        try:
            last = int(last)
        except:
            last = None

    MAX_TICKS = 200000
    if ticks < 1 or ticks > MAX_TICKS:
        return jsonify({"error": f"ticks must be between 1 and {MAX_TICKS}"}), 400

    if reset_seed:
        try:
            world.load_seed(WORLD_FILE)
        except Exception as e:
            return jsonify({"error": f"Failed to reload seed: {e}"}), 500

    try:
        for _ in range(ticks):
            world.step()
    except Exception as e:
        return jsonify({"error": f"Error during simulation: {e}"}), 500

    stats = world.get_stats(last_n=last)
    return jsonify({"stats": stats, "ticks_run": ticks})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
