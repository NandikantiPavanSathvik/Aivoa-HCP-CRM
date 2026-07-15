import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendChatMessage, clearChat } from '../store';
import { Send, Mic, Trash2, Cpu, Sparkles, Volume2, ChevronRight } from 'lucide-react';

const PROMPT_CHIPS = [
  "I met Dr. Jenkins today, discussed CardioSphere-10mg, she was very positive. Follow-up in 2 weeks.",
  "Had a video call with Dr. Chen about OncoShield-X patient enrollment. Neutral sentiment.",
  "Called Dr. Taylor about PediaMelt Iron drops — she was positive, no GI complaints.",
  "Sorry, change the sentiment to negative for the last entry.",
  "Show me Dr. Jenkins' interaction history.",
  "What should I do next with the selected HCP?",
];

const ChatCopilot = () => {
  const dispatch = useDispatch();
  const { messages, loading, lastToolsTriggered } = useSelector((state) => state.chat);
  const { selectedHcp } = useSelector((state) => state.hcps);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingProgress, setRecordingProgress] = useState(0);
  const chatEndRef = useRef(null);

  const mockTranscripts = [
    `Today I met with Dr. Sarah Jenkins at Metro Heart Clinic for an in-person visit. We discussed CardioSphere-10mg and the latest clinical trial results. She was very positive and enthusiastic — noted a 15% improvement in patient outcomes. She requested sample packs and brochures. Schedule a follow-up on 2026-07-28. Next step: deliver sample packs.`,
    `Had a video call with Dr. Robert Chen at City Cancer Center today. We discussed OncoShield-X patient enrollment for the Phase 3 trial. Sentiment was neutral — he raised questions about side-effect profiles and eligibility criteria. He wants safety data sheets by email. Follow-up on 2026-07-20.`,
    `Spoke to Dr. Emily Taylor over the phone today. Discussed PediaMelt Iron drops. She is highly positive — patients are tolerating it well due to the strawberry flavor. No GI complaints. She plans to increase prescribing for minor anemia cases. Schedule follow-up for 2026-08-05 by phone call.`,
    `Met with Dr. David Patel at Brain & Spine Institute. Discussed clinical data sheets and NeuroBoost product line. He was positive and wants safety brochures delivered by end of this week. Next step: email brochure PDF.`,
  ];

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = (textToSend = inputText) => {
    if (!textToSend.trim() || loading) return;

    // Build message history for backend context (last 6 messages only, no tool_calls)
    // Sending tool_calls in history confuses the model into generating malformed XML calls
    const history = messages.slice(-6).map(m => ({
      role: m.role,
      content: m.content,
      // Intentionally omit tool_calls — they cause the model to replicate tool patterns as text
    }));

    dispatch(sendChatMessage({
      message: textToSend,
      history,
      hcpId: selectedHcp?.id || null,
    }));

    setInputText('');
  };

  const handleChipClick = (chip) => {
    setInputText(chip);
  };

  // Simulate voice dictation
  const handleSimulateDictation = () => {
    if (isRecording || loading) return;
    setIsRecording(true);
    setRecordingProgress(0);

    let transcript = mockTranscripts[Math.floor(Math.random() * mockTranscripts.length)];
    if (selectedHcp) {
      if      (selectedHcp.id === 1) transcript = mockTranscripts[0];
      else if (selectedHcp.id === 2) transcript = mockTranscripts[1];
      else if (selectedHcp.id === 3) transcript = mockTranscripts[2];
      else if (selectedHcp.id === 4) transcript = mockTranscripts[3];
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

  const isFirstMessage = messages.length <= 1;

  return (
    <div className="chat-copilot glass-panel">
      <div className="chat-header">
        <div className="chat-header-title">
          <Sparkles className="text-primary animate-pulse" size={18} />
          <h3>AI Sales Copilot</h3>
          {selectedHcp && (
            <span className="chat-context-badge">
              Active: {selectedHcp.name.split(' ').slice(1).join(' ')}
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
              <div className="message-content" style={{ whiteSpace: 'pre-wrap' }}>
                {msg.content}
              </div>

              {/* Tool execution — show only tool names, no raw JSON */}
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="tool-logs">
                  <Cpu size={11} className="tool-icon" />
                  <span className="tool-log-summary">
                    AI used: {[...new Set(msg.tool_calls.map(t => t.name))].join(', ')}
                  </span>
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
              <span className="typing-text">LangGraph routing graph nodes…</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Prompt suggestion chips — shown when chat is empty/fresh */}
      {isFirstMessage && !loading && (
        <div className="prompt-chips-container">
          <p className="prompt-chips-label">Try saying:</p>
          <div className="prompt-chips">
            {PROMPT_CHIPS.map((chip, i) => (
              <button
                key={i}
                className="prompt-chip"
                onClick={() => handleChipClick(chip)}
                title={chip}
              >
                <ChevronRight size={10} />
                <span>{chip.length > 55 ? chip.slice(0, 55) + '…' : chip}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Voice dictation status bar */}
      {isRecording && (
        <div className="voice-status-bar">
          <Volume2 size={16} className="text-danger animate-pulse" />
          <span>Simulating Voice Input: dictating notes…</span>
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
          placeholder={
            selectedHcp
              ? `Describe what happened with ${selectedHcp.name.split(' ').slice(1).join(' ')}…`
              : 'Select an HCP first, or type your query…'
          }
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
