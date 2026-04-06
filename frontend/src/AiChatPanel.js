import React, { useState, useRef, useEffect } from 'react';
import { flushSync } from 'react-dom';
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

export default function AiChatPanel({ onFaultTreeGenerated, initialConversationId }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好！我是设备故障诊断助手。请描述您遇到的设备故障现象，我会帮您逐步分析定位问题。' }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  // 如果传入了初始会话 ID，挂载时加载历史记录
  useEffect(() => {
    if (initialConversationId) {
      loadConversation(initialConversationId);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 读取历史对话并恢复消息列表
  const loadConversation = async (convId) => {
    try {
      const resp = await fetch(`/api/conversations/${encodeURIComponent(convId)}`);
      if (!resp.ok) return;
      const conv = await resp.json();
      const msgs = [{ role: 'assistant', content: `已恢复对话「${conv.name}」，可继续提问。` }];
      for (const round of (conv.rounds || [])) {
        msgs.push({ role: 'user', content: round.question });
        const sources = Array.isArray(round.sources) ? round.sources : [];
        msgs.push({ role: 'assistant', content: round.answer, sources });
      }
      setConversationId(convId);
      setMessages(msgs);
    } catch (e) {
      console.error('加载历史对话失败', e);
    }
  };

  // 每次消息更新后自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = inputText.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputText('');
    setIsLoading(true);
    // 插入一个空的 assistant 消息占位，用于流式追加 token
    setMessages((prev) => [...prev, { role: 'assistant', content: '', streaming: true }]);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage,
          ...(conversationId ? { conversation_id: conversationId } : {}),
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`请求失败，状态码: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentSources = null;
      let eventType = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留不完整的行

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            let payload;
            try { payload = JSON.parse(line.slice(6)); } catch { continue; }

            if (eventType === 'conversation') {
              setConversationId(payload.conversation_id);
            } else if (eventType === 'sources') {
              currentSources = payload.sources;
            } else if (eventType === 'token') {
              // flushSync 强制 React 18 对每个 token 立即渲染，而非批量延迟
              flushSync(() => {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = { ...updated[updated.length - 1] };
                  last.content = (last.content || '') + payload.content;
                  updated[updated.length - 1] = last;
                  return updated;
                });
              });
            } else if (eventType === 'fault_tree') {
              const tree = payload.fault_tree;
              if (onFaultTreeGenerated) onFaultTreeGenerated(tree);
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { ...updated[updated.length - 1], faultTree: tree };
                return updated;
              });
            } else if (eventType === 'done') {
              const snapSources = currentSources;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content || payload.answer || '',
                  sources: snapSources,
                  streaming: false,
                };
                return updated;
              });
            } else if (eventType === 'error') {
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: `错误：${payload.message}`,
                  streaming: false,
                };
                return updated;
              });
            }
            eventType = null;
          }
        }
      }
      // 流读取完毕，确保 streaming 标志关闭
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === 'assistant' && last.streaming) {
          updated[updated.length - 1] = { ...last, sources: last.sources ?? currentSources, streaming: false };
        }
        return updated;
      });
    } catch (error) {
      if (error.name !== 'AbortError') {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: `请求出错：${error.message}`, streaming: false };
          } else {
            updated.push({ role: 'assistant', content: `请求出错：${error.message}` });
          }
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  // 开始新的对话
  const handleNewSession = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setConversationId(null);
    setIsLoading(false);
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
              <div style={{ fontWeight: 600, color: '#666' }}>📄 {src.file_name}</div>
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
        {conversationId && (
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={handleNewSession}>
            新会话
          </Button>
        )}
      </div>

      {/* 会话 ID 状态栏 */}
      {conversationId && (
        <div style={{
          padding: '6px 16px',
          borderBottom: '1px solid #f0f0f0',
          fontSize: 12,
          color: '#999',
          background: '#fafbfc',
        }}>
          <span>会话 #{conversationId.slice(0, 8)}</span>
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
