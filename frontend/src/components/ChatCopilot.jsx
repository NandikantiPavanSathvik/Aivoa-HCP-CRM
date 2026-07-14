import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendChatMessage, clearChat } from '../store';
import { Send, Mic, Trash2, Cpu, Wrench, Sparkles, Volume2 } from 'lucide-react';

const ChatCopilot = () => {
  const dispatch = useDispatch();
  const { messages, loading, lastToolsTriggered } = useSelector((state) => state.chat);
  const { selectedHcp } = useSelector((state) => state.hcps);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingProgress, setRecordingProgress] = useState(0);
  const chatEndRef = useRef(null);
  
  const mockTranscripts = [
    `Had a call with Dr. Sarah Jenkins today. We discussed CardioSphere-10mg. She was positive about the new trial results and wants a follow-up in-person meeting on 2026-07-20. Action item: deliver sample packs.`,
    `Met Dr. Robert Chen at City Cancer Center. Discussed OncoShield-X and patient enrollment. Sentiment was neutral. He had side-effect questions. Scheduled follow-up email next Monday.`,
    `Spoke to Dr. Emily Taylor. Discussed PediaMelt Iron drops. She is highly positive and says GI compliance is excellent. Schedule follow-up phone call for August 5th.`,
    `Met Dr. David Patel. Discussed clinical data sheets. He was positive and wants safety brochures by end of the week.`,
  ];

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = (textToSend = inputText) => {
    if (!textToSend.trim() || loading) return;
    
    // Construct message history for backend context (keep last 10 messages)
    const history = messages.slice(-10).map(m => ({
      role: m.role,
      content: m.content,
      tool_calls: m.tool_calls
    }));

    dispatch(sendChatMessage({
      message: textToSend,
      history,
      hcpId: selectedHcp?.id || null
    }));

    setInputText('');
  };

  // Simulate dictation
  const handleSimulateDictation = () => {
    if (isRecording || loading) return;
    setIsRecording(true);
    setRecordingProgress(0);

    // Pick a transcript based on current selected HCP if possible
    let transcript = mockTranscripts[Math.floor(Math.random() * mockTranscripts.length)];
    if (selectedHcp) {
      if (selectedHcp.id === 1) transcript = mockTranscripts[0];
      else if (selectedHcp.id === 2) transcript = mockTranscripts[1];
      else if (selectedHcp.id === 3) transcript = mockTranscripts[2];
    }

    const interval = setInterval(() => {
      setRecordingProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsRecording(false);
          setInputText(transcript);
          return 100;
        }
        return prev + 20;
      });
    }, 250);
  };

  const handleClear = () => {
    dispatch(clearChat());
  };

  return (
    <div className="chat-copilot glass-panel">
      <div className="chat-header">
        <div className="chat-header-title">
          <Sparkles className="text-primary animate-pulse" size={18} />
          <h3>AI Sales Copilot</h3>
          {selectedHcp && (
            <span className="chat-context-badge">
              Active: {selectedHcp.name.split(' ')[1]}
            </span>
          )}
        </div>
        <button onClick={handleClear} className="clear-chat-btn" title="Clear Chat">
          <Trash2 size={15} />
        </button>
      </div>

      {/* Messages Window */}
      <div className="messages-window">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.role}`}>
            <div className="message-bubble">
              <div className="message-content">{msg.content}</div>
              
              {/* Show tool executions inside assistant bubbles */}
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="tool-logs">
                  <div className="tool-log-header">
                    <Cpu size={12} className="tool-icon" />
                    <span>LangGraph Agent Executions:</span>
                  </div>
                  {msg.tool_calls.map((t, tid) => (
                    <div key={tid} className="tool-pill">
                      <Wrench size={10} className="tool-pill-icon" />
                      <span className="tool-pill-name">{t.name}</span>
                      <span className="tool-pill-args">{JSON.stringify(t.args)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message-row assistant">
            <div className="message-bubble typing-bubble">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className="typing-text">LangGraph routing graph nodes...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Simulated voice status or live waveforms */}
      {isRecording && (
        <div className="voice-status-bar">
          <Volume2 size={16} className="text-danger animate-pulse" />
          <span>Simulating Voice Input: dictating notes...</span>
          <div className="wave-animation">
            <span className="bar"></span>
            <span className="bar"></span>
            <span className="bar"></span>
            <span className="bar"></span>
            <span className="bar"></span>
          </div>
          <span className="progress-percent">{recordingProgress}%</span>
        </div>
      )}

      {/* Input Tray */}
      <div className="chat-input-container">
        <button 
          onClick={handleSimulateDictation}
          className={`voice-btn ${isRecording ? 'recording' : ''}`}
          disabled={loading}
          title="Simulate Voice Dictation"
        >
          <Mic size={18} />
        </button>
        <input
          type="text"
          placeholder={selectedHcp ? "Say what happened during the visit..." : "Select an HCP first or type query..."}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading}
          className="chat-input"
        />
        <button 
          onClick={() => handleSend()}
          className="send-btn" 
          disabled={!inputText.trim() || loading}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
};

export default ChatCopilot;
