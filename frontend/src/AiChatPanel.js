import React, { useState, useRef, useEffect } from 'react';
import { Panel } from '@xyflow/react';

export default function AiChatPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'ai', content: '你好！我是你的 AI 助手，有什么可以帮你的？' }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false); // 新增 loading 状态
  const messagesEndRef = useRef(null);

  // 每次消息更新后自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = inputText.trim();
    // 立即添加用户发送的消息
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputText('');
    setIsLoading(true);

    try {
      // 通过统一端口/代理发送请求
      const backendUrl = '/ai';
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userMessage, stream: true }),
      });

      if (!response.ok) {
        throw new Error(`请求失败，状态码: ${response.status}`);
      }

      // 准备读取流
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let aiMessageContent = '';
      let isFirstChunk = true;

      // 先添加一条空的 AI 消息，后续追加内容
      setMessages((prev) => [...prev, { role: 'ai', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        
        if (isFirstChunk) {
          setIsLoading(false); // 收到首个数据包时取消加载状态
          isFirstChunk = false;
        }

        if (done) break;
        
        // 追加解码后的文本块
        const chunkText = decoder.decode(value, { stream: true });
        aiMessageContent += chunkText;

        // 更新最后一条 AI 消息的内容
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = { role: 'ai', content: aiMessageContent };
          return newMessages;
        });
      }
    } catch (error) {
      console.error('AI 接口调用出错:', error);
      // 在界面上提示错误信息
      setMessages((prev) => [
        ...prev,
        { role: 'ai', content: `请求后端时出现错: ${error.message}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
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
          title="打开 AI 助手"
        >
          🤖
        </button>
      )}

      {/* 展开的聊天面板 */}
      {isOpen && (
        <div style={{
          width: '320px',
          height: '600px',
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
            padding: '12px 15px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontWeight: 'bold'
          }}>
            <span>🤖 AI 流程图助手</span>
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}
              title="收起聊天板"
            >
              ▼
            </button>
          </div>

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
                思考中... 🤔
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
              placeholder={isLoading ? 'AI 正在思考，请稍等...' : '问我任何关于图形的问题...'}
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
