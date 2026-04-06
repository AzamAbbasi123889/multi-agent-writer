import React from 'react';
import { Pencil, Sparkles, Network, Search, Keyboard, CheckCircle } from 'lucide-react';


const Sidebar = ({ topic, setTopic, isWriting, startPipeline, stopPipeline, resetPipeline, systemState, activeAgent }) => {
  
  const getStatusText = () => {
    switch (systemState) {
        case 'running': return 'Pipeline Active';
        case 'error': return 'Failed/Error';
        case 'complete': return 'Completed';
        default: return 'Ready';
    }
  };

  const agents = [
    { id: 'supervisor', name: 'Supervisor', icon: <Network size={14}/> },
    { id: 'researcher', name: 'Researcher', icon: <Search size={14}/> },
    { id: 'writer', name: 'Writer', icon: <Keyboard size={14}/> },
    { id: 'reviewer', name: 'Reviewer', icon: <CheckCircle size={14}/> },
  ];

  return (
    <aside className="sidebar">
      <div className="logo-container">
        <Pencil size={24} style={{ color: 'var(--accent)' }}/>
        <h2>AgentWriter</h2>
      </div>

      <div className="input-section">
        <label>What should we write about?</label>
        <div className="input-wrapper">
          <textarea 
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={isWriting}
            placeholder="Enter a topic... e.g., 'The Future of Electric Vehicles'"
          />
        </div>
        
        {!isWriting && systemState !== 'idle' ? (
          <button className="secondary-btn" onClick={resetPipeline} style={{ marginBottom: '0.5rem', width: '100%' }}>
            New Topic
          </button>
        ) : null}

        <div className="button-group" style={{ display: 'flex', gap: '0.5rem' }}>
          {!isWriting ? (
            <button 
              className="primary-btn" 
              onClick={startPipeline} 
              style={{ flex: 1 }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                Start Pipeline <Sparkles size={18} />
              </span>
            </button>
          ) : (
            <button 
              className="stop-btn" 
              onClick={stopPipeline}
              style={{ flex: 1 }}
            >
               <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                Stop Writing
              </span>
            </button>
          )}
        </div>
      </div>

      <div className="system-status">
        <h3>System Status</h3>
        <div className={`status-indicator ${systemState}`}>
          <span className="pulse"></span>
          <span>{getStatusText()}</span>
        </div>
      </div>

      <div className="agent-legend">
        <h3>Active Agents</h3>
        <ul>
          {agents.map(agent => (
            <li 
              key={agent.id} 
              className={`agent-tag ${agent.id} ${activeAgent === agent.id ? 'active' : ''}`}
            >
              {agent.icon} {agent.name}
              {activeAgent === agent.id && <span className="working-dot"></span>}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};

export default Sidebar;
