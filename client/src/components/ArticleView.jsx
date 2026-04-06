import React, { useState } from 'react';
import { FileText, FileSignature, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const ArticleView = ({ content, revisionCount, isWriting }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (content) {
      navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <section className="results-panel glass-panel" style={{ height: '60%' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <h3><FileText size={18} /> Final Article</h3>
          {content && (
            <button className="icon-btn" onClick={handleCopy} title="Copy to Clipboard">
              {copied ? <Check size={16} style={{ color: 'var(--color-writer)' }} /> : <Copy size={16} />}
            </button>
          )}
        </div>
        <div className="revision-badge">
          <span>Revision: {revisionCount}</span>
        </div>
      </div>
      <div className="article-content">
        {!content && !isWriting && (
          <div className="empty-state">
            <div className="empty-icon-wrapper">
              <FileSignature size={48} />
            </div>
            <p>Your AI-generated article will appear here.</p>
            <span className="subtitle">Start the pipeline to begin the writing process.</span>
          </div>
        )}
        {!content && isWriting && (
          <div className="empty-state writing-state">
            <div className="writing-animation">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
            <p>Agents are collaborating on your content...</p>
            <div className="skeleton-lines">
               <div className="skele-line" style={{ width: '80%' }}></div>
               <div className="skele-line" style={{ width: '95%' }}></div>
               <div className="skele-line" style={{ width: '60%' }}></div>
            </div>
          </div>
        )}
        {content && (
          <div className="markdown-body">
            <ReactMarkdown>{content}</ReactMarkdown>
            {isWriting && (
                <div className="writing-indicator-mini">
                    <span className="pulse"></span> Writing more...
                </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

export default ArticleView;
