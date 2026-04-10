import { useState, useCallback, useRef } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Button, Tooltip, Typography } from 'antd';
import {
  HomeOutlined, PlusOutlined, ApartmentOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import FileListPanel from './FileListPanel';
import ConversationHistoryPanel from './ConversationHistoryPanel';
import FaultTreeLibraryPanel from './FaultTreeLibraryPanel';
import './flow-chat.css';

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
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}

