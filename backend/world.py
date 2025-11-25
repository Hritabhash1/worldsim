import os
import json
import csv
from agent import Agent

INTERACTION_COOLDOWN_TICKS = 20


class World:
    def __init__(self, seed_file):
        self.agents = []
        self.pois = {}
        self.bounds = (0, 0, 24, 24)  # (min_x, min_y, max_x, max_y)
        self.tick_count = 0
        self.stats = []
        self.seed_file = seed_file

        if seed_file:
            self.load_seed(seed_file)

    # -------------------------------------------------------------
    # WORLD STEP
    # -------------------------------------------------------------
    def step(self, no_movement=False):
        """
        Advance world by one tick.
        If no_movement=True → skip built-in movement (LLM already moved agents).
        """
        self.tick_count += 1
        current_hour = self.tick_count % 24

        # -------- SCHEDULE --------
        for a in self.agents:
            try:
                if hasattr(a, "schedule") and current_hour in a.schedule:
                    a.goals = a.schedule[current_hour]
            except Exception:
                continue

        # ---------------------------------------------------------
        # HARD-CODED VENDOR BEHAVIOUR
        # Vendors always remain near canteen (8,15 ±1)
        # ---------------------------------------------------------
        if "canteen" in self.pois:
            cx, cy = self.pois["canteen"]

            for a in self.agents:
                if a.type == "vendor":

                    # allowed vendor zone = 3x3 around canteen
                    min_x, max_x = cx - 1, cx + 1
                    min_y, max_y = cy - 1, cy + 1

                    # If vendor is outside zone → snap back to canteen
                    if not (min_x <= a.x <= max_x and min_y <= a.y <= max_y):
                        a.x, a.y = cx, cy

                    # Vendor goals always force to canteen
                    a.goals = ["canteen"]

        # ---------------------------------------------------------
        # MOVEMENT (SAFE)
        # ---------------------------------------------------------
        if not no_movement:

            # Count crowd at POIs
            poi_counts = {p: 0 for p in self.pois}
            for a in self.agents:
                if a.goals and a.goals[0] in poi_counts:
                    poi_counts[a.goals[0]] += 1

            # Move agents
            for a in self.agents:

                # Vendor movement blocked (they stay near canteen)
                if a.type == "vendor":
                    continue

                # No goals → random walk
                if not a.goals:
                    if hasattr(a, "random_walk"):
                        a.random_walk(self.bounds)
                    continue

                target = a.goals[0]

                # If target is a valid POI and crowded, redirect
                if target in poi_counts and poi_counts[target] > 3:
                    alts = sorted(self.pois.keys(), key=lambda p: poi_counts[p])
                    if alts:
                        a.goals = [alts[0]]
                        target = alts[0]

                # Move towards target if valid POI
                if target in self.pois and hasattr(a, "move_towards"):
                    tx, ty = self.pois[target]
                    a.move_towards(tx, ty, speed=1)

                # If invalid target → random walk
                else:
                    if hasattr(a, "random_walk"):
                        a.random_walk(self.bounds)

        # ---------------------------------------------------------
        # INTERACTIONS
        # ---------------------------------------------------------
        interacted = set()
        for a in self.agents:
            for b in self.agents:
                if a.id == b.id:
                    continue

                pair = tuple(sorted([a.id, b.id]))
                if pair in interacted:
                    continue

                # Same tile → interact
                if a.x == b.x and a.y == b.y:

                    last_a = getattr(a, "last_interaction_tick", -999)
                    last_b = getattr(b, "last_interaction_tick", -999)

                    if self.tick_count - last_a < INTERACTION_COOLDOWN_TICKS:
                        interacted.add(pair)
                        continue
                    if self.tick_count - last_b < INTERACTION_COOLDOWN_TICKS:
                        interacted.add(pair)
                        continue

                    # Update stamps
                    a.last_interaction_tick = self.tick_count
                    b.last_interaction_tick = self.tick_count

                    # Store memory
                    try:
                        a.add_memory(f"Met {b.id} at tick {self.tick_count}", "interaction")
                    except:
                        pass

                    try:
                        b.add_memory(f"Met {a.id} at tick {self.tick_count}", "interaction")
                    except:
                        pass

                    interacted.add(pair)

        # ---------------------------------------------------------
        # STATS
        # ---------------------------------------------------------
        occ = {p: 0 for p in self.pois}
        for a in self.agents:
            for poi, pos in self.pois.items():
                if (a.x, a.y) == pos:
                    occ[poi] += 1

        self.stats.append({
            "tick": self.tick_count,
            "hour": current_hour,
            "occupancy": occ
        })

    # -------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------
    def get_stats(self, last_n=None):
        if last_n:
            return self.stats[-last_n:]
        return self.stats

    def export_stats_csv(self, out_file=None):
        if not out_file:
            out_file = os.path.join(os.path.dirname(self.seed_file), "stats.csv")

        headers = ["tick", "hour"] + list(self.pois.keys())
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for rec in self.stats:
                row = [rec["tick"], rec["hour"]]
                row.extend(rec["occupancy"].get(p, 0) for p in self.pois)
                writer.writerow(row)

        return out_file

    # -------------------------------------------------------------
    # LOAD SEED
    # -------------------------------------------------------------
    def load_seed(self, seed_file):
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.pois = {k: (int(v[0]), int(v[1])) for k, v in data.get("pois", {}).items()}

        self.agents = []
        for a in data.get("agents", []):
            self.agents.append(
                Agent(
                    a["id"],
                    a["type"],
                    x=a.get("x", 0),
                    y=a.get("y", 0),
                    goals=a.get("goals", []),
                    traits=a.get("traits", {})
                )
            )

        self.stats = []
        self.tick_count = 0
