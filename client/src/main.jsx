import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

console.log("Initializing React Mounting Sequence...");

const rootElement = document.getElementById('root');

if (!rootElement) {
    document.body.innerHTML = `
        <div style="background: red; color: white; padding: 20px; font-family: sans-serif;">
            <h1>Critical Error: DOM #root not found.</h1>
            <p>The React application cannot mount because the target container was not found in index.html.</p>
        </div>
    `;
} else {
    try {
        const root = ReactDOM.createRoot(rootElement);
        root.render(
            <React.StrictMode>
                <App />
            </React.StrictMode>
        );
        console.log("React mount successfully initiated.");
    } catch (e) {
        console.error("Mount Error Captured:", e);
        rootElement.innerHTML = `
            <div style="background: darkred; color: white; padding: 20px; border-radius: 8px;">
                <h2>Mount Failure</h2>
                <pre>${e.stack || e.message}</pre>
            </div>
        `;
    }
}
