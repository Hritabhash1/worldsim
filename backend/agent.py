# backend/agent.py
import time
import json
import math
import re
from typing import List, Dict

# Minimal stopwords list for tokenization
_STOPWORDS = {
    "the","a","an","and","or","is","are","was","were","in","on","at","to","for",
    "of","with","that","this","it","as","by","from","be","has","have","had","i",
    "you","he","she","they","we","my","your","their","our","but","not"
}

def tokenize(text: str) -> List[str]:
    """Lowercase, remove non-alphanum, split, remove stopwords."""
    text = text.lower()
    tokens = re.findall(r"\b[a-z0-9]{2,}\b", text)
    return [t for t in tokens if t not in _STOPWORDS]


class Agent:
    def __init__(
        self,
        id,
        type,
        x=0,
        y=0,
        goals=None,
        traits=None,
        personality=None
    ):
        self.id = id
        self.type = type
        self.x = int(x)
        self.y = int(y)
        self.goals = goals or []
        self.traits = traits or {}
        self.personality = personality or self.traits.get("personality", "")
        self.memory: List[Dict] = []
        self.created_at = int(time.time())
        self.schedule = self.generate_schedule()
        self.MEMORY_CAP = 500

        # Track previous movement to reduce spam
        self._last_logged_position = None


    # ------------------------------------------------------------------------
    # Memory Management
    # ------------------------------------------------------------------------
    def add_memory(self, text: str, source: str = "self"):
        """Add a memory with importance scoring + source boost."""
        ts = int(time.time())
        text = text.strip()
        if not text:
            return

        tokens = tokenize(text)

        length_score = min(1.0, len(text) / 200.0)
        token_score = min(1.0, len(tokens) / 30.0)
        recency_boost = 1.0

        # Boost LLM/Gemini/interaction-based memories
        source_boost = 1.0
        if source in ["interaction", "llm_interaction", "llm_dialogue", "gemini"]:
            source_boost += 0.15

        importance = (0.5 * length_score + 0.4 * token_score + 0.1 * recency_boost)
        importance *= source_boost

        mem = {
            "text": text,
            "ts": ts,
            "importance": round(float(importance), 4),
            "tokens": tokens,
            "source": source
        }

        self.memory.append(mem)

        if len(self.memory) > self.MEMORY_CAP:
            self.memory = self.memory[-self.MEMORY_CAP:]


    def get_recent_memories(self, n=5) -> List[Dict]:
        return list(reversed(self.memory[-n:]))


    def score_memory_for_query(self, mem: Dict, query_tokens: List[str], now_ts: int) -> float:
        """Relevance score = overlap × importance × recency."""
        mem_tokens = set(mem.get("tokens", []))
        overlap = len(mem_tokens.intersection(query_tokens))
        token_score = overlap / (1 + math.log(1 + len(mem_tokens))) if overlap else 0.0

        importance = float(mem.get("importance", 0.0))

        age_seconds = max(0, now_ts - int(mem.get("ts", now_ts)))
        age_hours = age_seconds / 3600.0
        recency = 1.0 / (1.0 + 0.1 * age_hours)

        score = token_score * 0.6 + importance * 0.3
        return float(score * recency)


    def retrieve_memories(self, query: str, top_n: int = 5) -> List[Dict]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return self.get_recent_memories(top_n)

        now_ts = int(time.time())
        scored = []

        for mem in self.memory:
            sc = self.score_memory_for_query(mem, query_tokens, now_ts)
            if sc > 0:
                scored.append((sc, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [m for _, m in scored[:top_n]]

        if len(top) < top_n:
            for r in self.get_recent_memories(top_n):
                if r not in top:
                    top.append(r)
                    if len(top) >= top_n:
                        break
        return top


    # ------------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------------
    def save_memories(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def load_memories(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded = []
        for item in data:
            if isinstance(item, dict) and "text" in item:
                item["tokens"] = tokenize(item.get("text", ""))
                item["ts"] = int(item.get("ts", int(time.time())))
                item["importance"] = float(item.get("importance", 0.0))
                loaded.append(item)

        self.memory = loaded[-self.MEMORY_CAP:]


    # ------------------------------------------------------------------------
    # Dictionary for frontend
    # ------------------------------------------------------------------------
    def to_dict(self):
        mem_texts = [m["text"] for m in self.get_recent_memories(8)]
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "goals": self.goals,
            "traits": self.traits,
            "personality": self.personality,
            "memory": mem_texts
        }


    # ------------------------------------------------------------------------
    # Movement (with spam reduction)
    # ------------------------------------------------------------------------
    def _log_position_if_changed(self):
        """Log movement only if position changed significantly."""
        pos = (self.x, self.y)
        if pos != self._last_logged_position:
            self.add_memory(f"Moved to {self.x},{self.y}", source="movement")
            self._last_logged_position = pos

    def random_walk(self, bounds=(0, 0, 24, 24)):
        import random
        minx, miny, maxx, maxy = bounds
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])

        self.x = max(min(self.x + dx, maxx), minx)
        self.y = max(min(self.y + dy, maxy), miny)

        self._log_position_if_changed()

    def move_towards(self, tx, ty, speed=1):
        if self.x < tx:
            self.x += min(speed, tx - self.x)
        elif self.x > tx:
            self.x -= min(speed, self.x - tx)

        if self.y < ty:
            self.y += min(speed, ty - self.y)
        elif self.y > ty:
            self.y -= min(speed, self.y - ty)

        self._log_position_if_changed()


    # ------------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------------
    def generate_schedule(self):
        if self.type == "student":
            return {9: ["library"], 13: ["canteen"], 16: ["ground"]}
        elif self.type == "professor":
            return {9: ["lab"], 12: ["canteen"], 15: ["office"]}
        elif self.type == "vendor":
            return {10: ["canteen"], 14: ["ground"]}
        else:
            return {}
