import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Input, Button, Tag, Collapse, Empty, Spin } from 'antd';
import { SendOutlined, PlusOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';

const { TextArea } = Input;

// 意图标签配置
const INTENT_CONFIG = {
  fault_diagnosis: { label: '故障诊断', color: '#40b586' },
  off_topic: { label: '非诊断话题', color: '#e67e22' },
  suggest_fault_tree: { label: '建议生成故障树', color: '#3498db' },
  fault_tree_generated: { label: '✅ 已生成故障树', color: '#8e44ad' },
};

export default function AiChatPanel({ onFaultTreeGenerated }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好！我是设备故障诊断助手。请描述您遇到的设备故障现象，我会帮您逐步分析定位问题。' }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [diagnosisSufficient, setDiagnosisSufficient] = useState(false);
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

        const faultTree = result.fault_tree || null;
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: result.reply.content,
            intent: result.reply.intent,
            sources: result.sources,
            faultTree,
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
    setMessages([
      { role: 'assistant', content: '新会话已创建。请描述您遇到的设备故障现象，我会帮您分析定位问题。' },
    ]);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderSources = (sources, index) => {
    if (!sources || sources.length === 0) return null;
    const items = [{
      key: `src-${index}`,
      label: <span style={{ fontSize: 12, color: '#40b586' }}>查看知识来源 ({sources.length})</span>,
      children: (
        <div style={{ maxHeight: 120, overflowY: 'auto' }}>
          {sources.map((src, i) => (
            <div key={i} style={{ marginBottom: 6, paddingBottom: 4, borderBottom: i < sources.length - 1 ? '1px dashed #eee' : 'none', fontSize: 12, color: '#888' }}>
              <div style={{ fontWeight: 600, color: '#666' }}>📄 {src.source}</div>
              <div>{src.page_content.length > 150 ? src.page_content.slice(0, 150) + '...' : src.page_content}</div>
            </div>
          ))}
        </div>
      ),
    }];
    return <Collapse ghost size="small" items={items} style={{ marginTop: 4 }} />;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#fafbfc' }}>
      {/* 顶部标题栏 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: '#fff',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <RobotOutlined style={{ fontSize: 18, color: '#40b586' }} />
          <span style={{ fontWeight: 600, fontSize: 15, color: '#1a1a2e' }}>故障诊断助手</span>
        </div>
        {sessionId && (
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={handleNewSession}>
            新会话
          </Button>
        )}
      </div>

      {/* 会话状态栏 */}
      {sessionId && (
        <div style={{
          padding: '6px 16px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 12,
          color: '#999',
          background: '#fafbfc',
        }}>
          <span>#{sessionId.slice(0, 8)}</span>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {diagnosisSufficient && <Tag color="blue" style={{ margin: 0, fontSize: 11 }}>信息充足</Tag>}
            <Tag color={sessionStatus === 'in_progress' ? 'green' : 'orange'} style={{ margin: 0, fontSize: 11 }}>
              {sessionStatus === 'in_progress' ? '诊断中' : sessionStatus === 'tree_generated' ? '已生成' : sessionStatus || ''}
            </Tag>
          </div>
        </div>
      )}

      {/* 聊天记录 */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}>
        {messages.length === 0 && (
          <Empty description="开始一段故障诊断对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
        {messages.map((msg, index) => (
          <div key={index} style={{
            display: 'flex',
            gap: 8,
            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
          }}>
            {/* 头像 */}
            <div style={{
              width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: msg.role === 'user' ? '#e0f7fa' : '#f0faf5',
              color: msg.role === 'user' ? '#006064' : '#40b586',
              fontSize: 14,
            }}>
              {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
            </div>
            <div style={{ maxWidth: '85%', minWidth: 0 }}>
              {/* 意图标签 */}
              {msg.role === 'assistant' && msg.intent && (
                <div style={{ marginBottom: 3 }}>
                  <Tag color={INTENT_CONFIG[msg.intent]?.color || '#999'} style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px' }}>
                    {INTENT_CONFIG[msg.intent]?.label || msg.intent}
                  </Tag>
                </div>
              )}
              {/* 消息气泡 */}
              <div style={{
                padding: '10px 14px',
                borderRadius: msg.role === 'user' ? '12px 2px 12px 12px' : '2px 12px 12px 12px',
                fontSize: 13,
                lineHeight: 1.6,
                background: msg.role === 'user' ? '#e0f7fa' : '#fff',
                color: msg.role === 'user' ? '#006064' : '#333',
                border: msg.role === 'user' ? 'none' : '1px solid #eee',
                wordBreak: 'break-word',
              }}>
                {msg.role === 'assistant' ? (
                  <div className="markdown-body">
                    <ReactMarkdown components={{
                      p: ({ children }) => <p style={{ margin: '3px 0' }}>{children}</p>,
                      ul: ({ children }) => <ul style={{ margin: '3px 0', paddingLeft: 18 }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ margin: '3px 0', paddingLeft: 18 }}>{children}</ol>,
                      li: ({ children }) => <li style={{ margin: '1px 0' }}>{children}</li>,
                      strong: ({ children }) => <strong style={{ color: '#1a1a1a' }}>{children}</strong>,
                      h3: ({ children }) => <div style={{ fontWeight: 600, fontSize: 14, margin: '4px 0 2px' }}>{children}</div>,
                      code: ({ children }) => <code style={{ background: '#f5f5f5', padding: '1px 4px', borderRadius: 3, fontSize: 12 }}>{children}</code>,
                      hr: () => <hr style={{ border: 'none', borderTop: '1px solid #f0f0f0', margin: '6px 0' }} />,
                    }}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                )}
              </div>
              {/* 知识来源 */}
              {msg.role === 'assistant' && renderSources(msg.sources, index)}
              {/* 故障树加载按钮 */}
              {msg.role === 'assistant' && msg.faultTree && onFaultTreeGenerated && (
                <Button
                  type="primary"
                  size="small"
                  onClick={() => onFaultTreeGenerated(msg.faultTree)}
                  style={{ marginTop: 6, background: '#8e44ad', borderColor: '#8e44ad', borderRadius: 6, width: '100%', fontWeight: 600 }}
                >
                  🌲 加载故障树到画布
                </Button>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div style={{
              width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: '#f0faf5', color: '#40b586', fontSize: 14,
            }}>
              <RobotOutlined />
            </div>
            <div style={{ padding: '10px 14px', borderRadius: '2px 12px 12px 12px', background: '#fff', border: '1px solid #eee', color: '#aaa', fontSize: 13 }}>
              <Spin size="small" /> <span style={{ marginLeft: 6 }}>诊断分析中...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 底部输入区 */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #f0f0f0', background: '#fff' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={isLoading ? 'AI 正在分析，请稍等...' : '描述设备故障现象...'}
            autoSize={{ minRows: 1, maxRows: 3 }}
            style={{ borderRadius: 8, fontSize: 13 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={isLoading || !inputText.trim()}
            style={{ background: '#40b586', borderColor: '#40b586', borderRadius: 8, height: 'auto' }}
          />
        </div>
      </div>
    </div>
  );
}
