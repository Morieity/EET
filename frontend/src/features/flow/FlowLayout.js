import { useState, useCallback, useRef } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Button, Tooltip, Typography } from 'antd';
import {
  HomeOutlined, PlusOutlined, ApartmentOutlined,
  MenuOutlined, MessageOutlined, FileOutlined,
} from '@ant-design/icons';
import FileListPanel from './components/sidebar/FileListPanel';
import ConversationHistoryPanel from './components/sidebar/ConversationHistoryPanel';
import FaultTreeLibraryPanel from './components/sidebar/FaultTreeLibraryPanel';
import './styles/layout.css';
import './styles/sidebar.css';

const { Text } = Typography;

export default function Flow() {
  const navigate = useNavigate();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarTab, setSidebarTab] = useState('history'); // 'history' | 'files' | 'trees'
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const isResizing = useRef(false);

  // 新建对话
  const handleNewChat = useCallback(() => {
    navigate('/flow');
  }, [navigate]);

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

  const tabs = [
    { key: 'history', label: '对话', icon: <MessageOutlined /> },
    { key: 'files', label: '文件', icon: <FileOutlined /> },
    { key: 'trees', label: '故障树', icon: <ApartmentOutlined /> },
  ];

  return (
    <div className="fc-layout">
      {/* ========== 左侧侧边栏 ========== */}
      <div
        className={`fc-sidebar ${sidebarCollapsed ? 'fc-sidebar--collapsed' : ''}`}
        style={sidebarCollapsed ? undefined : { width: sidebarWidth, minWidth: sidebarWidth }}
      >
        {/* 收起态：窄图标栏 */}
        <div className="fc-sidebar-icon-rail">
          <Tooltip title="展开侧边栏" placement="right">
            <Button type="text" icon={<MenuOutlined />}
              onClick={() => setSidebarCollapsed(false)} />
          </Tooltip>
          <Tooltip title="新建对话" placement="right">
            <Button type="text" icon={<PlusOutlined />}
              onClick={handleNewChat} />
          </Tooltip>
          <div className="fc-rail-divider" />
          {tabs.map(tab => (
            <Tooltip key={tab.key} title={tab.label} placement="right">
              <Button type="text" icon={tab.icon}
                style={sidebarTab === tab.key ? { background: 'var(--fc-sidebar-active-bg)', color: 'var(--fc-accent)' } : undefined}
                onClick={() => { setSidebarTab(tab.key); setSidebarCollapsed(false); }} />
            </Tooltip>
          ))}
          <div style={{ flex: 1 }} />
          <Tooltip title="返回首页" placement="right">
            <Button type="text" icon={<HomeOutlined />}
              onClick={() => navigate('/')} />
          </Tooltip>
        </div>

        {/* 展开态：完整内容 */}
        {/* 边栏顶部 */}
        <div className="fc-sidebar-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tooltip title="收起侧边栏">
              <Button type="text" size="small" icon={<MenuOutlined />}
                className="fc-sidebar-toggle"
                onClick={() => setSidebarCollapsed(true)} />
            </Tooltip>
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

        {/* 边栏 Tab 栏 — pill 样式 */}
        <div className="fc-sidebar-tabs">
          {tabs.map(tab => (
            <div
              key={tab.key}
              onClick={() => setSidebarTab(tab.key)}
              className={`fc-sidebar-tab ${sidebarTab === tab.key ? 'fc-sidebar-tab--active' : ''}`}
            >
              {tab.label}
            </div>
          ))}
        </div>

        {/* 边栏内容 */}
        <div className="fc-sidebar-list" style={{ display: sidebarTab === 'history' ? 'block' : 'none' }}>
          <ConversationHistoryPanel />
        </div>
        <div className="fc-sidebar-list" style={{ display: sidebarTab === 'files' ? 'block' : 'none' }}>
          <FileListPanel />
        </div>
        <div className="fc-sidebar-list" style={{ display: sidebarTab === 'trees' ? 'block' : 'none' }}>
          <FaultTreeLibraryPanel />
        </div>
      </div>

      {/* 侧边栏拖动手柄 */}
      {!sidebarCollapsed && (
        <div className="fc-sidebar-resize" onMouseDown={handleResizeMouseDown} />
      )}

      {/* ========== 右侧主区域 ========== */}
      <div className="fc-main">
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <Outlet context={{ collapseSidebar: () => setSidebarCollapsed(true) }} />
        </div>
      </div>
    </div>
  );
}

