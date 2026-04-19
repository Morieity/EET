import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Input, Button, Tag, Collapse, Empty, Spin, message } from 'antd';
import { useNavigate, useParams, useOutletContext } from 'react-router-dom';
import { SendOutlined, PlusOutlined, RobotOutlined, UserOutlined, LoadingOutlined, ApartmentOutlined } from '@ant-design/icons';
import FaultTreeCard from '../tree/FaultTreeCard';
import FaultTreeWorkspace from '../tree/FaultTreeWorkspace';
import { extractFaultTreeFromText } from '../../utils/faultTreeParser';
import { getFaultTree } from '../../services/faultTreeApi';
import { INTENT_CONFIG, DEFAULT_WELCOME_MESSAGE, PERSISTED_TREE_ID_PATTERN, createAssistantMessage } from '../../utils/constants';
import useChatStream from '../../hooks/useChatStream';
import useConversationLoader from '../../hooks/useConversationLoader';
import '../../styles/chat.css';

const { TextArea } = Input;

const ChatMessageItem = React.memo(function ChatMessageItem({
  msg,
  index,
  conversationId,
  handleViewFaultTree,
}) {
  let faultTree = msg.faultTree;
  let displayContent = msg.content;

  if (!faultTree && msg.role === 'assistant' && !msg.streaming && msg.content) {
    const extracted = extractFaultTreeFromText(msg.content);
    if (extracted) {
      faultTree = extracted.tree;
      displayContent = extracted.cleanedContent;
    }
  } else if (faultTree) {
    const extracted = extractFaultTreeFromText(msg.content);
    displayContent = extracted ? extracted.cleanedContent : msg.content;
  }

  if (faultTree && msg.faultTreeId && !faultTree.id) {
    faultTree = { ...faultTree, id: msg.faultTreeId };
  }

  if (faultTree && !faultTree.conversation_id && conversationId) {
    faultTree = { ...faultTree, conversation_id: conversationId };
  }

  const sourcesNode = !msg.sources || msg.sources.length === 0
    ? null
    : (
      <Collapse
        ghost
        size="small"
        items={[{
          key: `src-${index}`,
          label: <span style={{ fontSize: 12, color: '#40b586' }}>查看知识来源 ({msg.sources.length})</span>,
          children: (
            <div style={{ maxHeight: 120, overflowY: 'auto' }}>
              {msg.sources.map((src, i) => (
                <div key={i} style={{ marginBottom: 6, paddingBottom: 4, borderBottom: i < msg.sources.length - 1 ? '1px dashed #eee' : 'none', fontSize: 12, color: '#888' }}>
                  <div style={{ fontWeight: 600, color: '#666' }}>📄 {src.file_name}</div>
                  <div>{src.page_content.length > 150 ? src.page_content.slice(0, 150) + '...' : src.page_content}</div>
                </div>
              ))}
            </div>
          ),
        }]}
        style={{ marginTop: 4 }}
      />
    );

  return (
    <div className={`fc-msg-row ${msg.role === 'user' ? 'fc-msg-row--user' : ''}`}>
      <div className={`fc-avatar ${msg.role === 'user' ? 'fc-avatar--user' : 'fc-avatar--assistant'}`}>
        {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
      </div>
      <div style={{ maxWidth: '100%', minWidth: 0, flex: 1 }}>
        {msg.role !== 'user' && msg.intent && (
          <div style={{ marginBottom: 3 }}>
            <Tag color={INTENT_CONFIG[msg.intent]?.color || '#999'} style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px' }}>
              {INTENT_CONFIG[msg.intent]?.label || msg.intent}
            </Tag>
          </div>
        )}
        <div className={msg.role === 'user' ? 'fc-user-bubble' : 'fc-assistant-bubble'}>
          {msg.role === 'user' ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
          ) : (
            <div className="markdown-body fc-markdown">
              <ReactMarkdown components={{
                pre: ({ children }) => {
                  const src = children?.props?.children ? String(children.props.children) : '';
                  if (
                    src.includes('"fault_tree"') || src.includes('"top_event"') ||
                    src.includes('"gates"') || src.includes('"basic_events"') ||
                    (src.includes('"nodes"') && src.includes('"edges"'))
                  ) return null;
                  return <pre>{children}</pre>;
                },
              }}>
                {displayContent}
              </ReactMarkdown>
            </div>
          )}
        </div>
        {msg.role !== 'user' && sourcesNode}
        {msg.streaming && msg.streamingStep && !msg.content && (
          <div style={{ marginTop: 4, fontSize: 12, color: 'var(--fc-text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Spin size="small" /> <span>{msg.streamingStep}</span>
          </div>
        )}
        {!faultTree && msg.generatingTree && (
          <div className="fc-fault-tree-card" style={{ marginTop: 8 }}>
            <div className="fc-fault-tree-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ApartmentOutlined style={{ color: '#8e44ad' }} />
                <LoadingOutlined style={{ color: '#8e44ad' }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--fc-text-muted)' }}>故障树加载中...</span>
              </div>
            </div>
          </div>
        )}
        {faultTree && <FaultTreeCard tree={faultTree} onView={handleViewFaultTree} />}
      </div>
    </div>
  );
});

export default function AiChatPanel({ initialConversationId, injectedTree, onInjected, onConversationCreated, onViewFaultTree }) {
  const navigate = useNavigate();
  const { conversationId: routeConversationId } = useParams();
  const { collapseSidebar } = useOutletContext() || {};
  const [messages, setMessages] = useState(createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
  const [inputText, setInputText] = useState('');
  const [conversationId, setConversationIdRaw] = useState(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [activeTree, setActiveTree] = useState(null);
  const [splitRatio, setSplitRatio] = useState(33.333);
  const splitDragging = useRef(false);
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

    setShouldAutoScroll((prev) => (prev === isNearBottom ? prev : isNearBottom));
  }, []);

  // 每次消息更新后自动滚动到底部（如果用户在底部）
  useEffect(() => {
    if (shouldAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: isLoading ? 'auto' : 'smooth' });
    }
  }, [messages, shouldAutoScroll, isLoading]);

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

  const handleViewFaultTree = useCallback(async (tree) => {
    if (onViewFaultTree) {
      onViewFaultTree(tree);
      return;
    }

    const persistedTreeId = resolvePersistedTreeId(tree);
    if (!persistedTreeId) {
      message.warning('该轮对话未关联已保存的故障树 ID，无法准确跳转到对应画布');
      return;
    }

    collapseSidebar?.();
    try {
      const loadedTree = await getFaultTree(persistedTreeId);
      setActiveTree(loadedTree);
    } catch (err) {
      message.error('加载故障树失败: ' + err.message);
    }
  }, [onViewFaultTree, resolvePersistedTreeId, collapseSidebar]);

  const handleCloseTree = useCallback(() => {
    setActiveTree(null);
    setSplitRatio(33.333);
  }, []);

  const sendMessageRef = useRef(sendMessage);
  sendMessageRef.current = sendMessage;

  const handleSendToChat = useCallback(async (text) => {
    if (!text?.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: text.trim() }]);
    await sendMessageRef.current(text.trim(), conversationIdRef.current);
  }, []);

  const handleSplitMouseDown = useCallback((e) => {
    e.preventDefault();
    splitDragging.current = true;
    const onMouseMove = (ev) => {
      if (!splitDragging.current) return;
      const container = ev.target.closest?.('.fc-chat-split-container') || document.querySelector('.fc-chat-split-container');
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const ratio = ((ev.clientX - rect.left) / rect.width) * 100;
      setSplitRatio(Math.min(70, Math.max(20, ratio)));
    };
    const onMouseUp = () => {
      splitDragging.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`fc-chat-split-container ${activeTree ? 'fc-chat-split-container--split' : ''}`}>
    <div className="fc-chat-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', flex: activeTree ? `0 0 ${splitRatio}%` : 1, maxWidth: activeTree ? `${splitRatio}%` : undefined, minHeight: 0, background: 'var(--fc-main-bg)' }}>
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
        {messages.map((msg, index) => (
          <ChatMessageItem
            key={msg.id || index}
            msg={msg}
            index={index}
            conversationId={conversationIdRef.current}
            handleViewFaultTree={handleViewFaultTree}
          />
        ))}

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
    {activeTree && (
      <>
        <div className="fc-chat-split-resize" onMouseDown={handleSplitMouseDown} />
        <div className="fc-chat-split-tree">
          <FaultTreeWorkspace tree={activeTree} onBack={handleCloseTree} onSendToChat={handleSendToChat} />
        </div>
      </>
    )}
    </div>
  );
}
