import React, { useState, useRef, useEffect } from 'react';
import { Panel } from '@xyflow/react';

// 意图标签配置
const INTENT_CONFIG = {
  fault_diagnosis: { label: '故障诊断', color: '#40b586' },
  off_topic: { label: '非诊断话题', color: '#e67e22' },
  suggest_fault_tree: { label: '建议生成故障树', color: '#3498db' },
};

export default function AiChatPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好！我是设备故障诊断助手。请描述您遇到的设备故障现象，我会帮您逐步分析定位问题。' }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [diagnosisSufficient, setDiagnosisSufficient] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);

  // 每次消息更新后自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // 创建新会话（首条消息）
  const createSession = async (userMessage) => {
    const response = await fetch('/api/diagnosis/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initial_message: userMessage }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.message || `创建会话失败，状态码: ${response.status}`);
    }
    return response.json();
  };

  // 发送后续消息
  const sendMessage = async (sid, userMessage) => {
    const response = await fetch(`/api/diagnosis/sessions/${encodeURIComponent(sid)}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.message || `发送消息失败，状态码: ${response.status}`);
    }
    return response.json();
  };

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = inputText.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputText('');
    setIsLoading(true);

    try {
      let result;
      if (!sessionId) {
        // 首条消息 → 创建诊断会话
        result = await createSession(userMessage);
        setSessionId(result.session_id);
        setSessionStatus(result.status);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: result.reply.content,
            intent: result.reply.intent,
          },
        ]);
      } else {
        // 后续消息 → 发送到已有会话
        result = await sendMessage(sessionId, userMessage);
        setSessionStatus(result.status);
        setDiagnosisSufficient(result.diagnosis_sufficient || false);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: result.reply.content,
            intent: result.reply.intent,
            sources: result.sources,
          },
        ]);
      }
    } catch (error) {
      console.error('诊断接口调用出错:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `请求后端时出现错误: ${error.message}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // 开始新的诊断会话
  const handleNewSession = () => {
    setSessionId(null);
    setSessionStatus(null);
    setDiagnosisSufficient(false);
    setExpandedSources({});
    setMessages([
      { role: 'assistant', content: '新会话已创建。请描述您遇到的设备故障现象，我会帮您分析定位问题。' },
    ]);
  };

  const toggleSources = (index) => {
    setExpandedSources((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 渲染意图标签
  const renderIntentTag = (intent) => {
    if (!intent) return null;
    const config = INTENT_CONFIG[intent] || { label: intent, color: '#999' };
    return (
      <span style={{
        display: 'inline-block',
        fontSize: '11px',
        padding: '1px 6px',
        borderRadius: '4px',
        background: config.color,
        color: 'white',
        marginBottom: '4px',
      }}>
        {config.label}
      </span>
    );
  };

  // 渲染知识来源折叠区
  const renderSources = (sources, index) => {
    if (!sources || sources.length === 0) return null;
    const isExpanded = expandedSources[index];
    return (
      <div style={{ marginTop: '6px' }}>
        <button
          onClick={() => toggleSources(index)}
          style={{
            background: 'none',
            border: 'none',
            color: '#40b586',
            cursor: 'pointer',
            fontSize: '12px',
            padding: 0,
            textDecoration: 'underline',
          }}
        >
          {isExpanded ? '▼ 收起来源' : '▶ 查看知识来源'} ({sources.length})
        </button>
        {isExpanded && (
          <div style={{
            marginTop: '4px',
            padding: '6px 8px',
            background: '#f5f5f5',
            borderRadius: '4px',
            fontSize: '12px',
            color: '#666',
            maxHeight: '120px',
            overflowY: 'auto',
          }}>
            {sources.map((src, i) => (
              <div key={i} style={{ marginBottom: i < sources.length - 1 ? '6px' : 0, borderBottom: i < sources.length - 1 ? '1px dashed #ddd' : 'none', paddingBottom: '4px' }}>
                <div style={{ fontWeight: 'bold', color: '#555' }}>📄 {src.source}</div>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.3' }}>
                  {src.page_content.length > 150 ? src.page_content.slice(0, 150) + '...' : src.page_content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <Panel position="bottom-right" style={{ marginBottom: '180px', marginRight: '10px' }}>
      {/* 悬浮打开按钮（收起状态） */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            width: '50px',
            height: '50px',
            borderRadius: '50%',
            background: '#40b586',
            color: 'white',
            border: 'none',
            boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
            cursor: 'pointer',
            fontSize: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.2s',
          }}
          title="打开故障诊断助手"
        >
          🤖
        </button>
      )}

      {/* 展开的聊天面板 */}
      {isOpen && (
        <div style={{
          width: '360px',
          height: '620px',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid #eee',
          overflow: 'hidden'
        }}>
          {/* 标题栏 */}
          <div style={{
            background: '#40b586',
            color: 'white',
            padding: '10px 15px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontWeight: 'bold',
            fontSize: '14px',
          }}>
            <span>🔧 故障诊断助手</span>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {sessionId && (
                <button
                  onClick={handleNewSession}
                  style={{
                    background: 'rgba(255,255,255,0.25)',
                    border: '1px solid rgba(255,255,255,0.5)',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '12px',
                    borderRadius: '4px',
                    padding: '2px 8px',
                  }}
                  title="开始新的诊断会话"
                >
                  + 新会话
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}
                title="收起聊天面板"
              >
                ▼
              </button>
            </div>
          </div>

          {/* 会话状态栏 */}
          {sessionId && (
            <div style={{
              padding: '5px 15px',
              background: '#f0faf5',
              borderBottom: '1px solid #e0e0e0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '12px',
              color: '#666',
            }}>
              <span>会话: {sessionId.slice(0, 8)}...</span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {diagnosisSufficient && (
                  <span style={{
                    color: '#3498db',
                    fontWeight: 'bold',
                    fontSize: '11px',
                    padding: '1px 6px',
                    background: '#eaf4fd',
                    borderRadius: '4px',
                  }}>
                    ✅ 信息充足
                  </span>
                )}
                <span style={{
                  padding: '1px 6px',
                  borderRadius: '4px',
                  background: sessionStatus === 'in_progress' ? '#e8f5e9' : '#fff3e0',
                  color: sessionStatus === 'in_progress' ? '#2e7d32' : '#e65100',
                }}>
                  {sessionStatus === 'in_progress' ? '诊断中' : sessionStatus === 'tree_generated' ? '已生成故障树' : sessionStatus || ''}
                </span>
              </div>
            </div>
          )}

          {/* 聊天记录滚动区 */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '15px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: '#fafafa'
          }}>
            {messages.map((msg, index) => (
              <div key={index} style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
              }}>
                {/* 意图标签（仅 assistant 消息显示） */}
                {msg.role === 'assistant' && msg.intent && (
                  <div style={{ marginBottom: '2px' }}>{renderIntentTag(msg.intent)}</div>
                )}
                <div style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  lineHeight: '1.4',
                  background: msg.role === 'user' ? '#e0f7fa' : '#ffffff',
                  color: msg.role === 'user' ? '#006064' : '#333',
                  border: msg.role === 'user' ? 'none' : '1px solid #ddd',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap'
                }}>
                  {msg.content}
                </div>
                {/* 知识来源折叠区 */}
                {msg.role === 'assistant' && renderSources(msg.sources, index)}
              </div>
            ))}
            {/* 当处于加载状态时，展示 "思考中..." */}
            {isLoading && (
              <div style={{
                alignSelf: 'flex-start',
                padding: '8px 12px',
                borderRadius: '8px',
                fontSize: '14px',
                background: '#ffffff',
                color: '#888',
                border: '1px solid #eee',
                fontStyle: 'italic'
              }}>
                诊断分析中... 🤔
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 底部输入区 */}
          <div style={{ padding: '10px', background: 'white', borderTop: '1px solid #eee', display: 'flex', gap: '8px' }}>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder={isLoading ? 'AI 正在分析，请稍等...' : '描述设备故障现象...'}
              style={{
                flex: 1,
                resize: 'none',
                height: '40px',
                padding: '8px',
                borderRadius: '6px',
                border: '1px solid #ccc',
                fontSize: '13px',
                outline: 'none',
                fontFamily: 'inherit',
                opacity: isLoading ? 0.6 : 1
              }}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !inputText.trim()}
              style={{
                background: '#40b586',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                padding: '0 15px',
                cursor: (isLoading || !inputText.trim()) ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                transition: 'opacity 0.2s',
                opacity: (isLoading || !inputText.trim()) ? 0.6 : 1
              }}
            >
              发送
            </button>
          </div>
        </div>
      )}
    </Panel>
  );
}
