import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Input, Button, Tag, Collapse, Empty, Spin, message } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { SendOutlined, PlusOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import FaultTreeCard from '../tree/FaultTreeCard';
import { extractFaultTreeFromText } from '../../utils/faultTreeParser';
import { INTENT_CONFIG, DEFAULT_WELCOME_MESSAGE, PERSISTED_TREE_ID_PATTERN, createAssistantMessage } from '../../utils/constants';
import useChatStream from '../../hooks/useChatStream';
import useConversationLoader from '../../hooks/useConversationLoader';
import '../../styles/chat.css';

const { TextArea } = Input;

export default function AiChatPanel({ initialConversationId, injectedTree, onInjected, onConversationCreated, onViewFaultTree }) {
  const navigate = useNavigate();
  const { conversationId: routeConversationId } = useParams();
  const [messages, setMessages] = useState(createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
  const [inputText, setInputText] = useState('');
  const [conversationId, setConversationIdRaw] = useState(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const abortControllerRef = useRef(null);
  const conversationIdRef = useRef(null);

  const setConversationState = useCallback((nextConversationId) => {
    conversationIdRef.current = nextConversationId;
    setConversationIdRaw(nextConversationId);
  }, []);

  const { sendMessage, isStreaming, resetStreaming } = useChatStream({
    setMessages, setConversationState, abortControllerRef,
    onConversationCreated, routeConversationId, navigate,
  });

  const { handleNewSession } = useConversationLoader({
    routeConversationId, initialConversationId,
    setMessages, setConversationState, conversationIdRef,
    resetStreaming, navigate, injectedTree, onInjected,
  });

  const isLoading = isStreaming;

  // 检测用户是否向上滚动
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    // 获取当前滚动位置和容器高度
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    // 如果用户滚动到底部附近（距离底部 100px 以内），启用自动滚动
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    setShouldAutoScroll(isNearBottom);
  }, []);

  // 每次消息更新后自动滚动到底部（如果用户在底部）
  useEffect(() => {
    if (shouldAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, shouldAutoScroll]);

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;
    const userMessage = inputText.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputText('');
    await sendMessage(userMessage, conversationId);
  };

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
          <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--fc-text-primary)' }}>青色交流电灯</span>
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
      <div className="fc-chat-messages" ref={messagesContainerRef} onScroll={handleScroll}>
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
