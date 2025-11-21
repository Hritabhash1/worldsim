import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import "./App.css";

/* Agent info panel */
function AgentInfo({ agent, onClose }) {
  if (!agent) return null;
  return (
    <div className="agent-info">
      <button className="close" onClick={onClose}>✕</button>
      <h3>{agent.id} <span className="muted">({agent.type})</span></h3>
      <p><strong>Position:</strong> {agent.x}, {agent.y}</p>
      <p><strong>Goals:</strong> {agent.goals && agent.goals.join(", ")}</p>
      <div><strong>Recent Memory:</strong>
        <ul className="memory-list">
          { (agent.memory || []).slice().reverse().map((m, i) => <li key={i}>{m}</li>) }
        </ul>
      </div>
    </div>
  );
}

const agentIcon = (type) => {
  if (type === "student") return "🎓";
  if (type === "professor") return "👨‍🏫";
  if (type === "vendor") return "🍔";
  return "🧑";
};

export default function App() {
  const [agentsRaw, setAgentsRaw] = useState([]);
  const [pois, setPois] = useState({});
  const [statsLatest, setStatsLatest] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [running, setRunning] = useState(true);
  const tickRef = useRef(null);

  const scale = 20;
  const gridSize = 25;
  const mapSize = gridSize * scale;

  const [positions, setPositions] = useState({});

  const fetchWorld = async () => {
    try {
      const res = await axios.get("http://localhost:5000/api/world");
      const agents = res.data.agents || [];
      const pois = res.data.pois || {};
      setAgentsRaw(agents);
      setPois(pois);
      setPositions(prev => {
        const next = { ...prev };
        agents.forEach(a => {
          if (!next[a.id]) next[a.id] = { x: a.x * scale, y: a.y * scale };
        });
        return next;
      });
    } catch (err) {
      console.error("fetchWorld error", err);
    }
  };

  const fetchStatsLatest = async () => {
    try {
      const res = await axios.get("http://localhost:5000/api/stats?last=1");
      const s = (res.data && res.data.stats && res.data.stats.length) ? res.data.stats[0] : null;
      setStatsLatest(s);
    } catch (err) {
      console.error("fetchStats error", err);
    }
  };

  const doTick = async () => {
    try {
      await axios.post("http://localhost:5000/api/tick", {});
      await Promise.all([fetchWorld(), fetchStatsLatest()]);
    } catch (err) {
      console.error("tick error", err);
    }
  };

  useEffect(() => {
    fetchWorld();
    fetchStatsLatest();
    tickRef.current = setInterval(() => {
      if (running) doTick();
    }, 1800);
    return () => clearInterval(tickRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running]);

  useEffect(() => {
    let raf = null;
    const animate = () => {
      setPositions(prev => {
        const next = { ...prev };
        agentsRaw.forEach(a => {
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

  const poiCountsFromAgents = {};
  agentsRaw.forEach(a => {
    const t = a.goals && a.goals[0];
    if (t) poiCountsFromAgents[t] = (poiCountsFromAgents[t] || 0) + 1;
  });

  const getOccupancy = (poiName) => {
    if (statsLatest && statsLatest.occupancy) {
      return statsLatest.occupancy[poiName] || 0;
    }
    return poiCountsFromAgents[poiName] || 0;
  };

  const maxOcc = Math.max(1, ...Object.keys(pois).map(k => getOccupancy(k)));

  const handleAgentClick = (a) => setSelectedAgent(a);
  const handleMapClick = () => setSelectedAgent(null);

  const handleDownloadCSV = async () => {
    try {
      // download using browser
      const res = await axios.get("http://localhost:5000/api/export_stats", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'stats.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("download error", err);
      alert("Failed to download CSV. Check backend /api/export_stats.");
    }
  };

  const heatLegend = [1, Math.max(2, Math.ceil(maxOcc / 2)), maxOcc];

  return (
    <div className="App">
      <header className="header">
        <h1>🌍 WorldSim - Virtual BIT Mesra</h1>
        <div className="controls">
          <button onClick={() => setRunning(!running)}>{running ? "Pause" : "Resume"}</button>
          <button onClick={() => doTick()}>Step</button>
          <button onClick={handleDownloadCSV}>Download Stats CSV</button>
        </div>
      </header>

      <div className="content">
        <div className="map-wrapper">
          <div className="map" style={{ width: mapSize, height: mapSize }} onClick={handleMapClick}>

            {Object.entries(pois).map(([name, coord]) => {
              const [x, y] = coord;
              const occ = getOccupancy(name);
              const radius = 12 + (occ / (maxOcc || 1)) * 40;
              const opacity = Math.min(0.75, 0.15 + (occ / (maxOcc || 1)) * 0.7);
              return (
                <div key={`heat-${name}`} style={{ position: "absolute", left: x * scale, top: y * scale, transform: "translate(-50%,-50%)", pointerEvents: "none", zIndex: 1 }}>
                  <svg width={radius*2} height={radius*2} style={{ overflow: "visible" }}>
                    <circle cx={radius} cy={radius} r={radius} fill="red" opacity={opacity} />
                  </svg>
                </div>
              );
            })}

            {Object.entries(pois).map(([name, coord]) => {
              const [x, y] = coord;
              return (
                <div key={name} className="poi" style={{ left: `${x * scale}px`, top: `${y * scale}px` }} title={`${name} (occ: ${getOccupancy(name)})`}>
                  <div className="poi-dot" />
                  <div className="poi-label">{name}</div>
                </div>
              );
            })}

            {agentsRaw.map(a => {
              const pos = positions[a.id] || { x: a.x * scale, y: a.y * scale };
              return (
                <div
                  key={a.id}
                  className="agent"
                  onClick={(e) => { e.stopPropagation(); handleAgentClick(a); }}
                  style={{
                    left: `${pos.x}px`,
                    top: `${pos.y}px`,
                    zIndex: 5
                  }}
                  title={`${a.id} (${a.type})`}
                >
                  <span className="agent-emoji">{agentIcon(a.type)}</span>
                </div>
              );
            })}
          </div>

          <div className="heat-legend">
            <div><strong>Heat legend (occupancy)</strong></div>
            <div className="legend-row">
              {heatLegend.map((v, i) => (
                <div key={i} className="legend-item">
                  <div className="legend-dot" style={{ width: 12 + (i*10), height: 12 + (i*10), opacity: 0.4 + i*0.2 }} />
                  <div className="legend-label">{v}+</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar">
          <h2>Agents</h2>
          <div className="agent-list">
            {agentsRaw.map(a => (
              <div key={a.id} className="agent-row" onClick={() => setSelectedAgent(a)}>
                <span className="agent-dot" style={{ background: a.type === "student" ? "#4CAF50" : a.type === "professor" ? "#2196F3" : "#FF9800" }} />
                <span>{a.id} <span className="muted">({a.type})</span></span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16 }}>
            <h3>POI Popularity (latest)</h3>
            <div className="poi-stats">
              {Object.entries(pois).map(([name, _]) => {
                const count = getOccupancy(name);
                const width = Math.min(100, (count / (maxOcc || 1)) * 100);
                return (
                  <div key={name} className="poi-stat-row">
                    <div className="poi-stat-label">{name}</div>
                    <div className="poi-stat-bar-wrap">
                      <div className="poi-stat-bar" style={{ width: `${width}%` }} />
                    </div>
                    <div className="poi-stat-count">{count}</div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </div>

      <AgentInfo agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
    </div>
  );
}
