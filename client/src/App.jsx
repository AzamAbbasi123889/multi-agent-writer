import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Terminal from './components/Terminal';
import ArticleView from './components/ArticleView';

function App() {
  const [topic, setTopic] = useState('');
  const [isWriting, setIsWriting] = useState(false);
  const [systemState, setSystemState] = useState('idle'); // idle, running, error, complete
  const [logs, setLogs] = useState([{ type: 'system', msg: 'Welcome to Multi-Agent Writer. Enter a topic to begin...', timestamp: new Date() }]);
  const [articleContent, setArticleContent] = useState('');
  const [revisionCount, setRevisionCount] = useState(0);
  const [activeAgent, setActiveAgent] = useState(null); // supervisor, researcher, writer, reviewer

  const eventSourceRef = useRef(null);
  const readerRef = useRef(null);

  const addLog = (message, type = 'system', isError = false) => {
    setLogs(prev => [...prev, { msg: message, type, isError, timestamp: new Date() }]);
  };

  const clearLogs = () => {
    setLogs([{ type: 'system', msg: 'Logs cleared. Ready.', timestamp: new Date() }]);
  };

  const stopPipeline = () => {
    if (readerRef.current) {
        readerRef.current.cancel();
        readerRef.current = null;
    }
    setIsWriting(false);
    setSystemState('idle');
    setActiveAgent(null);
    addLog('Pipeline stopped by user.', 'system');
  };

  const resetPipeline = () => {
    setTopic('');
    setArticleContent('');
    setRevisionCount(0);
    setSystemState('idle');
    setActiveAgent(null);
    clearLogs();
  };

  const startPipeline = async () => {
    if (!topic.trim()) {
      addLog('Please enter a topic first.', 'error', true);
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setLogs([]); // Clear auto
    addLog(`Initiating pipeline for topic: "${topic}"`, 'system');
    setIsWriting(true);
    setSystemState('running');
    setRevisionCount(0);
    setArticleContent('');

    try {
      const response = await fetch('http://localhost:5000/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      // We read streams asynchronously
      const processStream = async () => {
        try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const messages = buffer.split("\n\n");
              buffer = messages.pop();

              for (const msg of messages) {
                if (msg.startsWith("data: ")) {
                  try {
                    const data = JSON.parse(msg.replace("data: ", ""));
                    handleSSEEvent(data);
                  } catch (e) {
                    console.error("Parse error:", e);
                  }
                }
              }
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.error("Stream reader error:", err);
            }
        } finally {
            // After stream is complete or stopped, make sure state is idle if not set to complete
            setSystemState(prev => (prev === 'running' ? 'idle' : prev));
            setIsWriting(false);
            setActiveAgent(null);
            readerRef.current = null;
        }
      };

      processStream();
    } catch (error) {
      addLog(`Connection failed: ${error.message}. Is the Flask server running?`, 'error', true);
      setSystemState('error');
      setIsWriting(false);
      setActiveAgent(null);
    }
  };

  const handleSSEEvent = (event) => {
    const { type, message, data } = event;

    switch (type) {
      case 'start':
      case 'llm':
      case 'supervisor':
        addLog(message, type);
        break;
      case 'warning':
      case 'error':
        addLog(`ERROR: ${message}`, 'error', true);
        if (type === 'error') {
            setSystemState('error');
            setIsWriting(false);
        }
        break;
      case 'agent_start':
      case 'agent_log':
      case 'agent_done':
        const agent = data?.agent || 'system';
        addLog(message, agent);
        setActiveAgent(agent);
        if (data?.content && agent === 'writer') {
          setArticleContent(data.content);
        }
        break;
      case 'complete':
        addLog("Pipeline completed successfully!", 'system');
        setSystemState('complete');
        setIsWriting(false);
        if (data?.draft) setArticleContent(data.draft);
        if (data?.revision_count !== undefined) setRevisionCount(data.revision_count);
        break;
      default:
        addLog(message, 'system');
    }
  };

  return (
    <div className="app-container">
      <Sidebar 
        topic={topic}
        setTopic={setTopic}
        isWriting={isWriting}
        startPipeline={startPipeline}
        stopPipeline={stopPipeline}
        resetPipeline={resetPipeline}
        systemState={systemState}
        activeAgent={activeAgent}
      />
      <main className="main-content" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem', overflow: 'hidden' }}>
        <Terminal logs={logs} clearLogs={clearLogs} />
        <ArticleView content={articleContent} revisionCount={revisionCount} isWriting={isWriting} />
      </main>
    </div>
  );
}

export default App;
