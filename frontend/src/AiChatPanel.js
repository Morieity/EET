import React, { useState, useRef, useEffect, useCallback } from 'react';
import { flushSync } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import { Input, Button, Tag, Collapse, Empty, Spin, message } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { SendOutlined, PlusOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import FaultTreeCard from './FaultTreeCard';
import { extractFaultTreeFromText } from './utils';
import './flow-chat.css';

const { TextArea } = Input;

// 意图标签配置
const INTENT_CONFIG = {
  fault_diagnosis: { label: '故障诊断', color: '#40b586' },
  off_topic: { label: '非诊断话题', color: '#e67e22' },
  suggest_fault_tree: { label: '建议生成故障树', color: '#3498db' },
  fault_tree_generated: { label: '✅ 已生成故障树', color: '#8e44ad' },
};

const DEFAULT_WELCOME_MESSAGE = '你好！我是设备故障诊断助手。请描述您遇到的设备故障现象，我会帮您逐步分析定位问题。';
const DEFAULT_NEW_SESSION_MESSAGE = '新会话已创建。请描述您遇到的设备故障现象，我会帮您分析定位问题。';
const PERSISTED_TREE_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function createAssistantMessage(content) {
  return [{ role: 'assistant', content }];
}

export default function AiChatPanel({ initialConversationId, injectedTree, onInjected, onConversationCreated, onViewFaultTree }) {
  const navigate = useNavigate();
  const { conversationId: routeConversationId } = useParams();
  const [messages, setMessages] = useState(createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  const conversationIdRef = useRef(null);
  const loadRequestRef = useRef(0);

  const setConversationState = useCallback((nextConversationId) => {
    conversationIdRef.current = nextConversationId;
    setConversationId(nextConversationId);
  }, []);

  const loadConversation = useCallback(async (convId, requestId) => {
    try {
      const resp = await fetch(`/api/conversations/${encodeURIComponent(convId)}`);
      if (requestId !== loadRequestRef.current) return;
      if (!resp.ok) {
        setConversationState(null);
        setMessages(createAssistantMessage('未找到该历史对话，请开始新的诊断会话。'));
        return;
      }
      const conv = await resp.json();
      if (requestId !== loadRequestRef.current) return;

      const roundTreeIds = [...new Set(
        (conv.rounds || [])
          .map((round) => round.fault_tree_id)
          .filter(Boolean)
      )];
      const roundTrees = new Map();

      if (roundTreeIds.length > 0) {
        const treeEntries = await Promise.all(roundTreeIds.map(async (treeId) => {
          try {
            const treeResp = await fetch(`/api/fault-trees/${encodeURIComponent(treeId)}`);
            if (!treeResp.ok) {
              return null;
            }
            const tree = await treeResp.json();
            return [treeId, tree];
          } catch (error) {
            console.error('加载轮次关联故障树失败', error);
            return null;
          }
        }));

        if (requestId !== loadRequestRef.current) return;

        treeEntries.filter(Boolean).forEach(([treeId, tree]) => {
          roundTrees.set(treeId, tree);
        });
      }

      const msgs = [];
      for (const round of (conv.rounds || [])) {
        msgs.push({ role: 'user', content: round.question });
        const sources = Array.isArray(round.sources) ? round.sources : [];
        msgs.push({
          role: 'assistant',
          content: round.answer,
          sources,
          faultTree: round.fault_tree_id ? roundTrees.get(round.fault_tree_id) || undefined : undefined,
          faultTreeId: round.fault_tree_id || null,
        });
      }
      setConversationState(convId);
      setMessages(msgs.length > 0 ? msgs : createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
    } catch (e) {
      if (requestId !== loadRequestRef.current) return;
      console.error('加载历史对话失败', e);
      setConversationState(null);
      setMessages(createAssistantMessage('加载历史对话失败，请稍后重试。'));
    }
  }, [setConversationState]);

  // 路由驱动会话恢复：只有当 URL 会话与当前本地会话不一致时才重新拉取。
  useEffect(() => {
    const nextConversationId = routeConversationId ?? initialConversationId ?? null;

    if (nextConversationId && nextConversationId === conversationIdRef.current) {
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    loadRequestRef.current += 1;
    setIsLoading(false);

    if (nextConversationId) {
      setMessages(createAssistantMessage('正在加载历史对话...'));
      loadConversation(nextConversationId, loadRequestRef.current);
      return;
    }

    setConversationState(null);
    setMessages(createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
  }, [routeConversationId, initialConversationId, loadConversation, setConversationState]);

  // T011: 外部注入故障树时追加 system 消息
  useEffect(() => {
    if (injectedTree) {
      setMessages((prev) => [...prev, { role: 'system', content: '已从故障树库加载', faultTree: injectedTree }]);
      onInjected?.();
    }
  }, [injectedTree]); // eslint-disable-line react-hooks/exhaustive-deps

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
    setMessages((prev) => [...prev, { role: 'assistant', content: '', streaming: true, streamingStep: '正在连接...' }]);

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
              setConversationState(payload.conversation_id);
              onConversationCreated?.();
              if (routeConversationId !== payload.conversation_id) {
                navigate(`/flow/${payload.conversation_id}`, { replace: true });
              }
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.streamingStep = '正在检索相关文档...';
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (eventType === 'sources') {
              currentSources = payload.sources;
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.streamingStep = payload.sources?.length
                  ? `已找到 ${payload.sources.length} 条相关文档，正在生成回复...`
                  : '正在生成回复...';
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (eventType === 'token') {
              // flushSync 强制 React 18 对每个 token 立即渲染，而非批量延迟
              flushSync(() => {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = { ...updated[updated.length - 1] };
                  last.content = (last.content || '') + payload.content;
                  last.streamingStep = null;
                  updated[updated.length - 1] = last;
                  return updated;
                });
              });
            } else if (eventType === 'fault_tree') {
              const tree = payload.fault_tree;
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.faultTree = tree;
                last.faultTreeId = tree?.id || last.faultTreeId || null;
                updated[updated.length - 1] = last;
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
                  faultTreeId: payload.fault_tree_id || last.faultTreeId || null,
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
  const handleNewSession = useCallback(() => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    loadRequestRef.current += 1;
    setConversationState(null);
    setIsLoading(false);
    setMessages(createAssistantMessage(DEFAULT_NEW_SESSION_MESSAGE));
    if (routeConversationId) {
      navigate('/flow');
    }
  }, [navigate, routeConversationId, setConversationState]);

  const resolvePersistedTreeId = useCallback((tree) => {
    const candidates = [tree?.id, tree?.fault_tree_id];

    for (const candidate of candidates) {
      const rawTreeId = candidate == null ? '' : String(candidate);
      if (PERSISTED_TREE_ID_PATTERN.test(rawTreeId)) {
        return rawTreeId;
      }
    }

    return null;
  }, []);

  const handleViewFaultTree = useCallback((tree) => {
    if (onViewFaultTree) {
      onViewFaultTree(tree);
      return;
    }

    const activeConversationId = tree?.conversation_id || conversationIdRef.current;
    if (!activeConversationId) {
      message.warning('当前会话尚未建立，暂时无法跳转到故障树页面');
      return;
    }

    const persistedTreeId = resolvePersistedTreeId(tree);
    if (!persistedTreeId) {
      message.warning('该轮对话未关联已保存的故障树 ID，无法准确跳转到对应画布');
      return;
    }

    navigate(`/flow/${activeConversationId}/${persistedTreeId}`);
  }, [navigate, onViewFaultTree, resolvePersistedTreeId]);

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
    <div className="fc-chat-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', flex: 1, minHeight: 0, background: 'var(--fc-main-bg)' }}>
      {/* 顶部标题栏 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--fc-main-border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'var(--fc-main-bg)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <RobotOutlined style={{ fontSize: 18, color: 'var(--fc-accent)' }} />
          <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--fc-text-primary)' }}>故障诊断助手</span>
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
          borderBottom: '1px solid var(--fc-main-border)',
          fontSize: 12,
          color: 'var(--fc-text-muted)',
          background: 'var(--fc-main-bg)',
        }}>
          <span>会话 #{conversationId.slice(0, 8)}</span>
        </div>
      )}

      {/* 聊天记录 */}
      <div className="fc-chat-messages">
        <div className="fc-msg-inner">
        {messages.length === 0 && (
          <Empty description="开始一段故障诊断对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
        {messages.map((msg, index) => {
          // 计算有效故障树和展示内容
          let faultTree = msg.faultTree;
          let displayContent = msg.content;
          if (!faultTree && msg.role === 'assistant' && !msg.streaming && msg.content) {
            const extracted = extractFaultTreeFromText(msg.content);
            if (extracted) {
              faultTree = extracted.tree;
              displayContent = extracted.cleanedContent;
            }
          } else if (faultTree) {
            // SSE 已提供故障树，仅过滤内容中的 JSON
            const extracted = extractFaultTreeFromText(msg.content);
            displayContent = extracted ? extracted.cleanedContent : msg.content;
          }

          if (faultTree && msg.faultTreeId && !faultTree.id) {
            faultTree = { ...faultTree, id: msg.faultTreeId };
          }
          if (faultTree && !faultTree.conversation_id && conversationIdRef.current) {
            faultTree = { ...faultTree, conversation_id: conversationIdRef.current };
          }

          return (
          <div key={index} className={`fc-msg-row ${msg.role === 'user' ? 'fc-msg-row--user' : ''}`}>
            {/* 头像 */}
            <div className={`fc-avatar ${msg.role === 'user' ? 'fc-avatar--user' : 'fc-avatar--assistant'}`}>
              {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
            </div>
            <div style={{ maxWidth: msg.role === 'user' ? '100%' : '100%', minWidth: 0, flex: 1 }}>
              {/* 意图标签 */}
              {msg.role !== 'user' && msg.intent && (
                <div style={{ marginBottom: 3 }}>
                  <Tag color={INTENT_CONFIG[msg.intent]?.color || '#999'} style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px' }}>
                    {INTENT_CONFIG[msg.intent]?.label || msg.intent}
                  </Tag>
                </div>
              )}
              {/* 消息气泡 */}
              <div className={msg.role === 'user' ? 'fc-user-bubble' : 'fc-assistant-bubble'}>
                {msg.role === 'user' ? (
                  <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                ) : (
                  <div className="markdown-body">
                    <ReactMarkdown components={{
                      p: ({ children }) => <p style={{ margin: '3px 0' }}>{children}</p>,
                      ul: ({ children }) => <ul style={{ margin: '3px 0', paddingLeft: 18 }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ margin: '3px 0', paddingLeft: 18 }}>{children}</ol>,
                      li: ({ children }) => <li style={{ margin: '1px 0' }}>{children}</li>,
                      strong: ({ children }) => <strong style={{ color: 'var(--fc-text-primary)' }}>{children}</strong>,
                      h3: ({ children }) => <div style={{ fontWeight: 600, fontSize: 14, margin: '4px 0 2px' }}>{children}</div>,
                      pre: ({ children }) => {
                        // 检测疑似故障树 JSON 代码块并隐藏
                        const src = children?.props?.children ? String(children.props.children) : '';
                        if (src.includes('"fault_tree"') || src.includes('"top_event"') ||
                            src.includes('"gates"') || src.includes('"basic_events"') ||
                            (src.includes('"nodes"') && src.includes('"edges"'))) return null;
                        return <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 6, overflow: 'auto', fontSize: 12 }}>{children}</pre>;
                      },
                      code: ({ children }) => (
                        <code style={{ background: '#f5f5f5', padding: '1px 4px', borderRadius: 3, fontSize: 12 }}>{children}</code>
                      ),
                      hr: () => <hr style={{ border: 'none', borderTop: '1px solid var(--fc-main-border)', margin: '6px 0' }} />,
                    }}>
                      {displayContent}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
              {/* 知识来源 */}
              {msg.role !== 'user' && renderSources(msg.sources, index)}
              {/* 流式步骤指示器 */}
              {msg.streaming && msg.streamingStep && !msg.content && (
                <div style={{ marginTop: 4, fontSize: 12, color: 'var(--fc-text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Spin size="small" /> <span>{msg.streamingStep}</span>
                </div>
              )}
              {/* 故障树卡片 */}
              {faultTree && <FaultTreeCard tree={faultTree} onView={handleViewFaultTree} />}
            </div>
          </div>
          );
        })}

        <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 底部输入区 */}
      <div className="fc-input-area">
        <div className="fc-input-inner">
          <TextArea
            className="fc-composer-input"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={isLoading ? 'AI 正在分析，请稍等...' : '描述设备故障现象...'}
            autoSize={{ minRows: 1, maxRows: 3 }}
            style={{ fontSize: 14 }}
          />
          <div className="fc-composer-toolbar">
            <div className="fc-composer-hint">
              {isLoading ? (
                <>
                  <Spin size="small" />
                  <span>AI 正在分析中...</span>
                </>
              ) : (
                <span>Enter 发送，Shift + Enter 换行</span>
              )}
            </div>
            <Button
              className="fc-send-button"
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={isLoading || !inputText.trim()}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
