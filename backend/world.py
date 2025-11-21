import json
import csv
import os
from agent import Agent

class World:
    def __init__(self, seed_file):
        self.agents = []
        self.pois = {}
        self.bounds = (0, 0, 24, 24)  # 25x25 grid
        self.tick_count = 0
        self.stats = []  # list of dicts per tick
        self.seed_file = seed_file
        self.load_seed(seed_file)

    def step(self):
        """Advance the world by 1 tick (hour). Also update stats."""
        self.tick_count += 1
        current_hour = self.tick_count % 24

        # --- Update goals based on schedules (if agent has schedule) ---
        for a in self.agents:
            if hasattr(a, "schedule") and current_hour in a.schedule:
                a.goals = a.schedule[current_hour]

        # --- Count intended targets per POI (before movement) ---
        poi_counts = {poi: 0 for poi in self.pois}
        for a2 in self.agents:
            if a2.goals:
                target = a2.goals[0]
                if target in poi_counts:
                    poi_counts[target] += 1

        # --- Move agents and apply crowding logic ---
        for a in self.agents:
            if a.goals:
                target = a.goals[0]

                # If crowded (> threshold), pick an alternative POI
                threshold = 3
                if poi_counts.get(target, 0) > threshold:
                    alternatives = [p for p in self.pois if p != target]
                    if alternatives:
                        # choose the least crowded alternative (simple heuristic)
                        alternatives_sorted = sorted(alternatives, key=lambda p: poi_counts.get(p, 0))
                        a.goals[0] = alternatives_sorted[0]
                        target = a.goals[0]

                # Move toward target if valid
                if target in self.pois:
                    tx, ty = self.pois[target]
                    a.move_towards(tx, ty, speed=1)
                else:
                    a.random_walk(bounds=self.bounds)
            else:
                a.random_walk(bounds=self.bounds)

        # --- Interaction logging (after movement) ---
        for a in self.agents:
            for other in self.agents:
                if other.id != a.id and a.x == other.x and a.y == other.y:
                    interaction = f"Met {other.id} ({other.type}) at {a.x},{a.y}"
                    # log once per tick per meeting
                    if not any(interaction in mem for mem in a.memory[-2:]):
                        a.log(interaction)

        # --- Update stats for this tick (POI occupancy after movement) ---
        occupancy = {poi: 0 for poi in self.pois}
        for a in self.agents:
            # count agent if they are at exact POI coordinates (on the dot)
            for poi, coord in self.pois.items():
                if (a.x, a.y) == tuple(coord):
                    occupancy[poi] += 1

        tick_record = {
            "tick": self.tick_count,
            "hour": current_hour,
            "occupancy": occupancy
        }
        self.stats.append(tick_record)

    def get_stats(self, last_n=None):
        """Return stats (optionally last n ticks)."""
        if last_n:
            return self.stats[-last_n:]
        return self.stats

    def export_stats_csv(self, out_file=None):
        """Export stats to CSV with columns: tick,hour,poi1,poi2,..."""
        if out_file is None:
            out_file = os.path.join(os.path.dirname(self.seed_file), "stats.csv")
        # prepare header
        poi_names = list(self.pois.keys())
        header = ["tick", "hour"] + poi_names

        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for rec in self.stats:
                row = [rec.get("tick"), rec.get("hour")]
                occ = rec.get("occupancy", {})
                for p in poi_names:
                    row.append(occ.get(p, 0))
                writer.writerow(row)
        return out_file

    def load_seed(self, seed_file):
        """Load agents and POIs from JSON seed file."""
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # POIs
        self.pois = {}
        for k, v in data.get("pois", {}).items():
            # store as list/tuple of ints
            self.pois[k] = (int(v[0]), int(v[1]))

        # Agents
        self.agents = []
        for a in data.get("agents", []):
            ag = Agent(
                a["id"],
                a["type"],
                x=a.get("x", 0),
                y=a.get("y", 0),
                goals=a.get("goals", []),
                traits=a.get("traits", {})
            )
            self.agents.append(ag)
        # clear stats when re-loading world
        self.stats = []
        self.tick_count = 0
