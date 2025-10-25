import json
from agent import Agent

class World:
    def __init__(self, seed_file):
        self.agents = []
        self.pois = {}
        self.bounds = (0,0,24,24)
        self.load_seed(seed_file)

    def load_seed(self, seed_file):
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.pois = data.get("pois", {})
        for k,v in list(self.pois.items()):
            self.pois[k] = (int(v[0]), int(v[1]))
        self.agents = []
        for a in data.get("agents", []):
            ag = Agent(a["id"], a["type"], a.get("x",0), a.get("y",0),
                       goals=a.get("goals", []), traits=a.get("traits", {}))
            self.agents.append(ag)

    def step(self):
        for a in self.agents:
            if a.goals:
                target = a.goals[0]
                if target in self.pois:
                    tx, ty = self.pois[target]
                    a.move_towards(tx, ty, speed=1)
                else:
                    a.random_walk(bounds=self.bounds)
            else:
                a.random_walk(bounds=self.bounds)
