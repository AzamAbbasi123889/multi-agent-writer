import React, { useEffect, useRef, useState } from 'react';
import { Terminal as TermIcon, Trash2, Filter } from 'lucide-react';

const Terminal = ({ logs, clearLogs }) => {
  const terminalRef = useRef(null);
  const [filter, setFilter] = useState('all'); // all, agents, system

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs, filter]);

  const getTimeStamp = (date) => {
    const d = new Date(date);
    return `[${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}]`;
  };

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true;
    if (filter === 'agents') return ['researcher', 'writer', 'reviewer', 'supervisor'].includes(log.type);
    if (filter === 'system') return ['system', 'error', 'llm'].includes(log.type);
    return true;
  });

  return (
    <section className="events-panel glass-panel" style={{ height: '40%' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <h3><TermIcon size={18} /> Live Agent Activity</h3>
          <div className="filter-group">
            <button 
              className={`filter-btn ${filter === 'all' ? 'active' : ''}`} 
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button 
              className={`filter-btn ${filter === 'agents' ? 'active' : ''}`} 
              onClick={() => setFilter('agents')}
            >
              Agents
            </button>
            <button 
              className={`filter-btn ${filter === 'system' ? 'active' : ''}`} 
              onClick={() => setFilter('system')}
            >
              System
            </button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="icon-btn" title="Clear Logs" onClick={clearLogs}>
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      <div className="terminal-content" ref={terminalRef}>
        {filteredLogs.length === 0 ? (
          <div className="empty-logs">No logs to display for this filter.</div>
        ) : (
          filteredLogs.map((log, i) => {
            let badgeHtml = null;
            const agentTypes = ['researcher', 'writer', 'reviewer', 'supervisor'];
            if (agentTypes.includes(log.type)) {
              badgeHtml = <span className={`log-badge ${log.type}`}>{log.type}</span>;
            } else if (log.type === 'llm') {
              badgeHtml = <span className="log-badge system">ai</span>;
            }

            return (
              <div key={i} className={`log-entry ${log.type} ${log.isError ? 'error' : ''}`}>
                <span className="timestamp">{getTimeStamp(log.timestamp)}</span>
                {badgeHtml}
                <span className="message">{log.msg}</span>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
};

export default Terminal;
