import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Tooltip, Typography } from 'antd';
import {
  HomeOutlined, PlusOutlined, ApartmentOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import AiChatPanel from './AiChatPanel';
import FileListPanel from './FileListPanel';
import ConversationHistoryPanel from './ConversationHistoryPanel';
import FaultTreeLibraryPanel from './FaultTreeLibraryPanel';
import FaultTreeWorkspace from './FaultTreeWorkspace';
import './flow-chat.css';

const { Text } = Typography;

export default function Flow() {
  const navigate = useNavigate();
  const [chatKey, setChatKey] = useState(0);
  const [activeConvId, setActiveConvId] = useState(null);
  const [injectedTree, setInjectedTree] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarTab, setSidebarTab] = useState('history'); // 'history' | 'files' | 'trees'
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [convRefreshTrigger, setConvRefreshTrigger] = useState(0);
  const [mainView, setMainView] = useState('chat'); // 'chat' | 'tree'
  const [activeTree, setActiveTree] = useState(null);
  const isResizing = useRef(false);

  // 从历史对话面板切换到 AI 对话并恢复该会话
  const handleSelectConversation = useCallback((convId) => {
    setActiveConvId(convId);
    setChatKey(k => k + 1);
  }, []);

  // 从故障树库加载 → 直接打开画布编辑器
  const handleLoadFaultTree = useCallback((tree) => {
    setActiveTree(tree);
    setMainView('tree');
  }, []);

  // 新建对话
  const handleNewChat = useCallback(() => {
    setActiveConvId(null);
    setChatKey(k => k + 1);
  }, []);

  // 对话创建/更新时刷新历史列表
  const handleConversationCreated = useCallback(() => {
    setConvRefreshTrigger(n => n + 1);
  }, []);

  // 从聊天消息中的故障树卡片进入完整编辑视图
  const handleViewFaultTree = useCallback((tree) => {
    setActiveTree(tree);
    setMainView('tree');
  }, []);

  const handleBackToChat = useCallback(() => {
    setMainView('chat');
  }, []);

  // 侧边栏拖动调整宽度
  const handleResizeMouseDown = useCallback((e) => {
    e.preventDefault();
    isResizing.current = true;
    const startX = e.clientX;
    const startWidth = sidebarWidth;
    const onMouseMove = (ev) => {
      if (!isResizing.current) return;
      const newWidth = Math.min(500, Math.max(180, startWidth + ev.clientX - startX));
      setSidebarWidth(newWidth);
    };
    const onMouseUp = () => {
      isResizing.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, [sidebarWidth]);

  return (
    <div className="fc-layout">
      {/* ========== 左侧深色边栏 ========== */}
      <div
        className={`fc-sidebar ${sidebarCollapsed ? 'fc-sidebar--collapsed' : ''}`}
        style={sidebarCollapsed ? undefined : { width: sidebarWidth, minWidth: sidebarWidth }}
      >
        {/* 边栏顶部 */}
        <div className="fc-sidebar-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApartmentOutlined style={{ fontSize: 18, color: 'var(--fc-accent)' }} />
            <Text strong style={{ fontSize: 15, color: 'var(--fc-sidebar-text)' }}>故障树诊断</Text>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <Tooltip title="新建对话">
              <Button type="text" size="small" icon={<PlusOutlined />} onClick={handleNewChat}
                style={{ color: 'var(--fc-sidebar-text-muted)' }} />
            </Tooltip>
            <Tooltip title="返回首页">
              <Button type="text" size="small" icon={<HomeOutlined />} onClick={() => navigate('/')}
                style={{ color: 'var(--fc-sidebar-text-muted)' }} />
            </Tooltip>
          </div>
        </div>

        {/* 边栏 Tab 栏 */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--fc-sidebar-border)', flexShrink: 0 }}>
          {[
            { key: 'history', label: '对话' },
            { key: 'files', label: '文件' },
            { key: 'trees', label: '故障树' },
          ].map(tab => (
            <div
              key={tab.key}
              onClick={() => setSidebarTab(tab.key)}
              style={{
                flex: 1,
                textAlign: 'center',
                padding: '8px 4px',
                fontSize: 12,
                cursor: 'pointer',
                fontWeight: sidebarTab === tab.key ? 600 : 400,
                color: sidebarTab === tab.key ? 'var(--fc-accent)' : 'var(--fc-sidebar-text-muted)',
                borderBottom: sidebarTab === tab.key ? '2px solid var(--fc-accent)' : '2px solid transparent',
                userSelect: 'none',
              }}
            >
              {tab.label}
            </div>
          ))}
        </div>

        {/* 边栏内容 */}
        <div className="fc-sidebar-list" style={{ display: sidebarTab === 'history' ? 'block' : 'none' }}>
          <ConversationHistoryPanel onSelectConversation={handleSelectConversation} refreshTrigger={convRefreshTrigger} />
        </div>
        <div className="fc-sidebar-list" style={{ display: sidebarTab === 'files' ? 'block' : 'none' }}>
          <FileListPanel />
        </div>
        <div className="fc-sidebar-list" style={{ display: sidebarTab === 'trees' ? 'block' : 'none' }}>
          <FaultTreeLibraryPanel onLoadTree={handleLoadFaultTree} />
        </div>
      </div>

      {/* 侧边栏拖动手柄 */}
      {!sidebarCollapsed && (
        <div className="fc-sidebar-resize" onMouseDown={handleResizeMouseDown} />
      )}

      {/* ========== 右侧主区域 ========== */}
      <div className="fc-main" style={{ position: 'relative' }}>
        {/* 折叠按钮 */}
        <Tooltip title={sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'}>
          <Button
            type="text"
            size="small"
            icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setSidebarCollapsed(c => !c)}
            className="fc-collapse-btn"
          />
        </Tooltip>
        <div style={{ flex: 1, minHeight: 0, display: mainView === 'chat' ? 'flex' : 'none', flexDirection: 'column' }}>
          <AiChatPanel
            key={chatKey}
            initialConversationId={activeConvId}
            injectedTree={injectedTree}
            onInjected={() => setInjectedTree(null)}
            onConversationCreated={handleConversationCreated}
            onViewFaultTree={handleViewFaultTree}
          />
        </div>
        {activeTree && (
          <div style={{ flex: 1, minHeight: 0, display: mainView === 'tree' ? 'flex' : 'none', flexDirection: 'column' }}>
            <FaultTreeWorkspace tree={activeTree} onBack={handleBackToChat} />
          </div>
        )}
      </div>
    </div>
  );
}

