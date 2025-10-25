import random
import time

class Agent:
    def __init__(self, id, type, x, y, goals=None, traits=None):
        self.id = id
        self.type = type
        self.x = int(x)
        self.y = int(y)
        self.goals = goals or []
        self.traits = traits or {}
        self.memory = []
        self.created_at = int(time.time())

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "goals": self.goals,
            "traits": self.traits,
            "memory": self.memory[-10:]
        }

    def random_walk(self, bounds=(0,0,24,24)):
        minx, miny, maxx, maxy = bounds
        dx = random.choice([-1,0,1])
        dy = random.choice([-1,0,1])
        self.x = max(min(self.x + dx, maxx), minx)
        self.y = max(min(self.y + dy, maxy), miny)
        self.log(f"Moved to {self.x},{self.y}")

    def move_towards(self, tx, ty, speed=1):
        if self.x < tx: self.x += min(speed, tx - self.x)
        elif self.x > tx: self.x -= min(speed, self.x - tx)
        if self.y < ty: self.y += min(speed, ty - self.y)
        elif self.y > ty: self.y -= min(speed, self.y - ty)
        self.log(f"Moved towards {tx},{ty}")

    def log(self, text):
        ts = int(time.time())
        self.memory.append(f"{ts}: {text}")
        if len(self.memory) > 100:
            self.memory = self.memory[-100:]
