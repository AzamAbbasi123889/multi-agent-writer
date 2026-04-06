document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const topicInput = document.getElementById('topicInput');
    const terminal = document.getElementById('terminal');
    const articleContent = document.getElementById('articleContent');
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    
    const connState = document.getElementById('connectionState');
    const statusIndicator = document.querySelector('.status-indicator');
    const revisionCountText = document.getElementById('revisionCountText');

    let eventSource = null;

    // Initialize UI
    topicInput.focus();

    // Helper to format time
    const getTimeStamp = () => {
        const now = new Date();
        return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    };

    // Helper to add log to terminal
    const addLog = (message, agentType = 'system', isError = false) => {
        const entry = document.createElement('div');
        entry.className = `log-entry ${agentType} ${isError ? 'error' : ''}`;
        
        let badgeHtml = '';
        if (agentType !== 'system' && agentType !== 'llm' && agentType !== 'error') {
            badgeHtml = `<span class="log-badge">${agentType}</span>`;
        }

        entry.innerHTML = `
            <span class="timestamp">[${getTimeStamp()}]</span>
            ${badgeHtml}
            <span class="message">${message}</span>
        `;
        
        terminal.appendChild(entry);
        // Scroll to bottom smoothly
        terminal.scrollTop = terminal.scrollHeight;
    };

    const updateStatus = (state, text) => {
        statusIndicator.className = `status-indicator ${state}`;
        connState.textContent = text;
    };

    const setWritingState = (isWriting) => {
        startBtn.disabled = isWriting;
        topicInput.disabled = isWriting;
        if (isWriting) {
            startBtn.innerHTML = '<span class="pulse" style="background:#fff"></span> Writing...';
            articleContent.innerHTML = `
                <div class="empty-state writing-skeleton">
                    <i class="fa-solid fa-pen-nib fa-bounce"></i>
                    <p>Agents are actively researching and drafting...</p>
                </div>
            `;
            updateStatus('running', 'Pipeline Active');
        } else {
            startBtn.innerHTML = '<span class="btn-text">Start Writing Pipeline</span><i class="fa-solid fa-wand-magic-sparkles"></i>';
        }
    };

    clearLogsBtn.addEventListener('click', () => {
        terminal.innerHTML = '<div class="log-entry system">Logs cleared. Ready.</div>';
    });

    startBtn.addEventListener('click', async () => {
        const topic = topicInput.value.trim();
        if (!topic) {
            addLog('Please enter a topic first.', 'error', true);
            topicInput.focus();
            return;
        }

        // Close existing SSE if any
        if (eventSource) {
            eventSource.close();
        }

        terminal.innerHTML = ''; // Auto clear on start
        addLog(`Initiating pipeline for topic: "${topic}"`, 'system');
        setWritingState(true);
        revisionCountText.textContent = `Round: 0`;

        try {
            // Step 1: Trigger the backend pipeline via POST request
            const response = await fetch('http://localhost:5000/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            // Step 2: Read SSE directly from the response body since the backend returns SSE immediately
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                
                // Process complete SSE messages split by double newline
                const messages = buffer.split("\n\n");
                // Keep the last part if it's incomplete
                buffer = messages.pop();

                for (const msg of messages) {
                    if (msg.startsWith("data: ")) {
                        const jsonStr = msg.replace("data: ", "");
                        try {
                            const data = JSON.parse(jsonStr);
                            handleEvent(data);
                        } catch (e) {
                            console.error("Error parsing SSE JSON:", e, jsonStr);
                        }
                    }
                }
            }

            // Stream finished naturally
            if (connState.textContent !== 'Completed') {
                 updateStatus('idle', 'Process Finished');
                 setWritingState(false);
            }

        } catch (error) {
            addLog(`Connection failed: ${error.message}. Is the Flask server running?`, 'error', true);
            updateStatus('error', 'Connection Error');
            setWritingState(false);
        }
    });

    const handleEvent = (event) => {
        const type = event.type;
        const msg = event.message;
        const data = event.data || {};

        switch (type) {
            case 'start':
                addLog(msg, 'system');
                break;
            case 'llm':
                addLog(msg, 'llm');
                break;
            case 'warning':
                addLog(msg, 'error', true);
                break;
            case 'error':
                addLog(`ERROR: ${msg}`, 'error', true);
                updateStatus('error', 'Failed');
                setWritingState(false);
                break;
            case 'supervisor':
                addLog(msg, 'supervisor');
                break;
            case 'agent_start':
            case 'agent_log':
            case 'agent_done':
                const agent = data.agent || 'system';
                addLog(msg, agent);
                
                // If it's a draft completion or we get content back
                if (data.content && agent === 'writer') {
                    // We parse markdown here
                    articleContent.innerHTML = marked.parse(data.content);
                }
                break;
            case 'complete':
                addLog("Pipeline completed successfully!", 'system');
                updateStatus('idle', 'Completed');
                setWritingState(false);
                
                if (data.draft) {
                    articleContent.innerHTML = marked.parse(data.draft);
                }
                if (data.revision_count !== undefined) {
                    revisionCountText.textContent = `Round: ${data.revision_count}`;
                }
                break;
            default:
                addLog(msg, 'system');
        }
    };
});
