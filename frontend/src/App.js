import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import "./App.css";

/* ========================= Agent Info Panel ========================= */
function AgentInfo({ agent, onClose, onThink }) {
  if (!agent) return null;

  return (
    <div className="agent-info">
      <button className="close" onClick={onClose}>✕</button>

      <h3>
        {agent.id} <span className="muted">({agent.type})</span>
      </h3>

      <p><strong>Position:</strong> {agent.x}, {agent.y}</p>
      <p><strong>Goals:</strong> {agent.goals && agent.goals.join(", ")}</p>

      {/* THINK button */}
      <button
        onClick={() => onThink(agent.id)}
        style={{
          marginTop: "10px",
          padding: "6px 12px",
          background: "#4a90e2",
          color: "white",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
          fontWeight: "bold"
        }}
      >
        🤖 THINK
      </button>

      {/* Recent memory */}
      <div style={{ marginTop: "12px" }}>
        <strong>Recent Memory:</strong>
        <ul className="memory-list">
          {(agent.memory || [])
            .slice()
            .reverse()
            .map((m, i) => (
              <li key={i}>{m}</li>
            ))}
        </ul>
      </div>

      {/* NEW LLM DECISION BLOCK */}
      {agent.lastLLM && (
        <div
          style={{
            marginTop: "15px",
            padding: "12px",
            borderRadius: "8px",
            background: "#eef5ff",
            border: "1px solid #c7dbff"
          }}
        >
          <h4>🤖 LLM Decision</h4>
          <p><strong>Thought:</strong> {agent.lastLLM.thought}</p>
          <p><strong>Action:</strong> {agent.lastLLM.action}</p>
          {/* <p><strong>Next Goal:</strong> {agent.lastLLM.next_goal || "None"}</p> */}
        </div>
      )}
    </div>
  );
}

/* ========================= Stats Modal ========================= */
function StatsModal({ open, onClose, stats, pois }) {
  if (!open) return null;

  const downloadCSV = () => {
    if (!stats || stats.length === 0) return;

    const poiNames = Object.keys(pois);
    const header = ["tick", "hour", ...poiNames];
    const lines = [header.join(",")];

    stats.forEach((rec) => {
      const row = [rec.tick, rec.hour];
      poiNames.forEach((p) => row.push(rec.occupancy[p] || 0));
      lines.push(row.join(","));
    });

    const csv = lines.join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "run_stats.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const poiNames = Object.keys(pois);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Simulation Stats</h3>
          <button className="close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {!stats || stats.length === 0 ? (
            <div className="muted">No stats available.</div>
          ) : (
            <div className="stats-table-wrap">
              <table className="stats-table">
                <thead>
                  <tr>
                    <th>tick</th>
                    <th>hour</th>
                    {poiNames.map((p) => (
                      <th key={p}>{p}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stats.map((rec, i) => (
                    <tr key={i}>
                      <td>{rec.tick}</td>
                      <td>{rec.hour}</td>
                      {poiNames.map((p) => (
                        <td key={p}>{rec.occupancy[p] || 0}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={downloadCSV}>Download CSV</button>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

/* ========================= Agent Icon ========================= */
const agentIcon = (type) => {
  if (type === "student") return "🎓";
  if (type === "professor") return "👨‍🏫";
  if (type === "vendor") return "🍔";
  return "🧑";
};

/* ========================= MAIN APP ========================= */
export default function App() {
  const [agentsRaw, setAgentsRaw] = useState([]);
  const [pois, setPois] = useState({});
  const [statsLatest, setStatsLatest] = useState(null);

  const [selectedAgent, setSelectedAgent] = useState(null);

  const [running, setRunning] = useState(true);
  const [simModalOpen, setSimModalOpen] = useState(false);
  const [simStats, setSimStats] = useState(null);
  const [simRunning, setSimRunning] = useState(false);
  const [simTicksInput, setSimTicksInput] = useState(240);

  const tickRef = useRef(null);

  const scale = 20;
  const gridSize = 25;
  const mapSize = gridSize * scale;

  const [positions, setPositions] = useState({});

  /* ========================= THINK BUTTON ========================= */
  const handleThink = async (agentId) => {
    try {
      const res = await axios.post("http://localhost:5000/api/agent_llm", {
        agent_id: agentId,
      });

      if (res.data.error) {
        console.error("AI Error:", res.data);
        return;
      }

      const llm = res.data.llm_result;

      // store LLM block inside UI
      setSelectedAgent((prev) => ({
        ...prev,
        lastLLM: llm,
      }));

      fetchWorld(); // refresh for memory update
    } catch (err) {
      console.error("AI request failed:", err);
    }
  };

  /* ========================= FETCH WORLD ========================= */
  const fetchWorld = async () => {
    try {
      const res = await axios.get("http://localhost:5000/api/world");
      setAgentsRaw(res.data.agents);
      setPois(res.data.pois);

      setPositions((prev) => {
        const next = { ...prev };
        res.data.agents.forEach((a) => {
          if (!next[a.id]) next[a.id] = { x: a.x * scale, y: a.y * scale };
        });
        return next;
      });

      // update lastLLM with fresh agent data if same selected
      if (selectedAgent) {
        const updated = res.data.agents.find((a) => a.id === selectedAgent.id);
        if (updated) {
          setSelectedAgent((prev) => ({
            ...updated,
            lastLLM: prev.lastLLM,
          }));
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  /* ========================= FETCH LATEST STATS ========================= */
  const fetchStatsLatest = async () => {
    try {
      const res = await axios.get(
        "http://localhost:5000/api/stats?last=1"
      );
      if (res.data.stats?.length) {
        setStatsLatest(res.data.stats[0]);
      }
    } catch {}
  };

  /* ========================= TICK ========================= */
  const doTick = async () => {
    try {
      await axios.post("http://localhost:5000/api/tick", { steps: 1 });
      await Promise.all([fetchWorld(), fetchStatsLatest()]);
    } catch (err) {
      console.error(err);
    }
  };

  /* ========================= AUTORUN LOOP ========================= */
  useEffect(() => {
    fetchWorld();
    fetchStatsLatest();

    tickRef.current = setInterval(() => {
      if (running) doTick();
    }, 1800);

    return () => clearInterval(tickRef.current);
  }, [running]);

  /* ========================= SMOOTH MOVEMENT ========================= */
  useEffect(() => {
    let raf;

    const animate = () => {
      setPositions((prev) => {
        const next = { ...prev };

        agentsRaw.forEach((a) => {
          const tx = a.x * scale;
          const ty = a.y * scale;
          if (!next[a.id]) next[a.id] = { x: tx, y: ty };

          const cur = next[a.id];
          const dx = tx - cur.x;
          const dy = ty - cur.y;
          const step = 0.22;

          if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
            cur.x += dx * step;
            cur.y += dy * step;
          } else {
            cur.x = tx;
            cur.y = ty;
          }
        });

        return next;
      });

      raf = requestAnimationFrame(animate);
    };

    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [agentsRaw]);

  /* ========================= RUN SERVER SIM ========================= */
  const handleRunSimJSON = async () => {
    setSimRunning(true);
    setSimModalOpen(true);
    setSimStats(null);

    try {
      const body = { ticks: Number(simTicksInput || 240), reset_seed: true };
      const res = await axios.post(
        "http://localhost:5000/api/run_sim_json",
        body
      );
      setSimStats(res.data.stats || []);
    } catch (err) {
      console.error(err);
      setSimStats([]);
    } finally {
      setSimRunning(false);
      fetchWorld();
      fetchStatsLatest();
    }
  };

  /* ========================= HEATMAP ========================= */
  const poiCounts = {};
  agentsRaw.forEach((a) => {
    const g = a.goals?.[0];
    if (g) poiCounts[g] = (poiCounts[g] || 0) + 1;
  });

  const getOcc = (p) =>
    statsLatest?.occupancy?.[p] || poiCounts[p] || 0;

  const maxOcc = Math.max(
    1,
    ...Object.keys(pois).map((p) => getOcc(p))
  );

  /* ========================= RENDER ========================= */
  return (
    <div className="App">
      <header className="header">
        <h1>🌍 WorldSim - Virtual BIT Mesra</h1>

        <div className="controls">
          <button onClick={() => setRunning(!running)}>
            {running ? "Pause" : "Resume"}
          </button>

          <button onClick={() => doTick()}>Step</button>

          <button
            onClick={() => {
              axios
                .get("http://localhost:5000/api/export_stats", {
                  responseType: "blob",
                })
                .then((res) => {
                  const url = window.URL.createObjectURL(
                    new Blob([res.data])
                  );
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "stats.csv";
                  a.click();
                  URL.revokeObjectURL(url);
                })
                .catch(() => alert("Failed to download CSV"));
            }}
          >
            Download Stats CSV
          </button>

          <div className="run-sim-inline">
            <input
              type="number"
              value={simTicksInput}
              min={1}
              onChange={(e) => setSimTicksInput(e.target.value)}
            />
            <button onClick={handleRunSimJSON} disabled={simRunning}>
              {simRunning ? "Running..." : "Run Simulation"}
            </button>
          </div>
        </div>
      </header>

      <div className="content">
        {/* MAP */}
        <div className="map-wrapper">
          <div
            className="map"
            style={{ width: mapSize, height: mapSize }}
            onClick={() => setSelectedAgent(null)}
          >
            {/* HEAT CIRCLES */}
            {Object.entries(pois).map(([name, coord]) => {
              const [x, y] = coord;
              const occ = getOcc(name);
              const r = 12 + (occ / maxOcc) * 40;
              const op = Math.min(0.75, 0.15 + (occ / maxOcc) * 0.7);

              return (
                <div
                  key={name + "_heat"}
                  style={{
                    position: "absolute",
                    left: x * scale,
                    top: y * scale,
                    transform: "translate(-50%,-50%)",
                    pointerEvents: "none",
                    zIndex: 1,
                  }}
                >
                  <svg width={r * 2} height={r * 2}>
                    <circle
                      cx={r}
                      cy={r}
                      r={r}
                      fill="red"
                      opacity={op}
                    ></circle>
                  </svg>
                </div>
              );
            })}

            {/* POIs */}
            {Object.entries(pois).map(([name, coord]) => {
              const [x, y] = coord;

              return (
                <div
                  key={name}
                  className="poi"
                  title={`${name} (occ: ${getOcc(name)})`}
                  style={{ left: x * scale, top: y * scale }}
                >
                  <div className="poi-dot" />
                  <div className="poi-label">{name}</div>
                </div>
              );
            })}

            {/* AGENTS */}
            {agentsRaw.map((a) => {
              const pos =
                positions[a.id] || {
                  x: a.x * scale,
                  y: a.y * scale,
                };

              return (
                <div
                  key={a.id}
                  className="agent"
                  style={{ left: pos.x, top: pos.y, zIndex: 6 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedAgent(a);
                  }}
                >
                  <span className="agent-emoji">
                    {agentIcon(a.type)}
                  </span>
                </div>
              );
            })}
          </div>

          {/* HEAT LEGEND */}
          {/* <div className="heat-legend">
            <strong>Heat legend</strong>
            <div className="legend-row">
              {[1, Math.ceil(maxOcc / 2), maxOcc].map(
                (v, i) => (
                  <div key={i} className="legend-item">
                    <div
                      className="legend-dot"
                      style={{
                        width: 12 + i * 10,
                        height: 12 + i * 10,
                        opacity: 0.4 + i * 0.2,
                      }}
                    />
                    <div className="legend-label">{v}+</div>
                  </div>
                )
              )}
            </div>
          </div> */}
        </div>

        {/* SIDE PANEL */}
        <div className="sidebar">
          <h2>Agents</h2>
          <div className="agent-list">
            {agentsRaw.map((a) => (
              <div
                key={a.id}
                className="agent-row"
                onClick={() => setSelectedAgent(a)}
              >
                <span
                  className="agent-dot"
                  style={{
                    background:
                      a.type === "student"
                        ? "#4caf50"
                        : a.type === "professor"
                        ? "#2196F3"
                        : "#FF9800",
                  }}
                />
                <span>
                  {a.id}{" "}
                  <span className="muted">({a.type})</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* INFO + MODALS */}
      <AgentInfo
        agent={selectedAgent}
        onClose={() => setSelectedAgent(null)}
        onThink={handleThink}
      />

      <StatsModal
        open={simModalOpen}
        onClose={() => setSimModalOpen(false)}
        stats={simStats}
        pois={pois}
      />
    </div>
  );
}
