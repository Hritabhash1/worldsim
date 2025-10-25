from flask import Flask, jsonify, request
from flask_cors import CORS
from world import World
import os

app = Flask(__name__)
CORS(app)

WORLD_FILE = os.path.join(os.path.dirname(__file__), "data", "world_seed.json")
world = World(WORLD_FILE)

@app.route("/api/agents", methods=["GET"])
def get_agents():
    return jsonify([a.to_dict() for a in world.agents])

@app.route("/api/tick", methods=["POST"])
def tick():
    steps = int(request.json.get("steps", 1)) if request.json else 1
    for _ in range(steps):
        world.step()
    return jsonify({"status":"ok", "agents":[a.to_dict() for a in world.agents]})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
