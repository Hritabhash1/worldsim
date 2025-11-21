class Agent:
    def __init__(self, id, type, x=0, y=0, goals=None, traits=None):
        self.id = id
        self.type = type
        self.x = int(x)
        self.y = int(y)
        self.goals = goals or []
        self.traits = traits or {}
        self.memory = []
        self.schedule = self.generate_schedule()

    def generate_schedule(self):
        """Simple routine per type."""
        if self.type == "student":
            return {9:["library"], 13:["canteen"], 16:["ground"]}
        elif self.type == "professor":
            return {9:["lab"], 12:["canteen"], 15:["office"]}
        elif self.type == "vendor":
            return {10:["canteen"], 14:["ground"]}
        else:
            return {}

    def move_towards(self, tx, ty, speed=1):
        """Move one step toward target."""
        if self.x < tx: self.x += speed
        elif self.x > tx: self.x -= speed
        if self.y < ty: self.y += speed
        elif self.y > ty: self.y -= speed

    def random_walk(self, bounds):
        min_x, min_y, max_x, max_y = bounds
        import random
        self.x += random.choice([-1,0,1])
        self.y += random.choice([-1,0,1])
        self.x = max(min_x, min(self.x, max_x))
        self.y = max(min_y, min(self.y, max_y))

    def log(self, msg):
        self.memory.append(msg)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "goals": self.goals,
            "memory": self.memory[-5:],  # last 5 interactions
            "traits": self.traits
        }
