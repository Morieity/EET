import React, { useMemo, useState, useCallback } from 'react';
import { Button, Tooltip, Typography, Tree, Tag, message } from 'antd';
import { CloudUploadOutlined, ApartmentOutlined, BranchesOutlined } from '@ant-design/icons';
import { convertFaultTreeToTreeData } from './utils';
import './flow-chat.css';

const { Text } = Typography;

/**
 * 自定义 Tree 节点标题渲染：事件名（描述）
 */
function TreeNodeTitle({ title, description, isGate, gateType }) {
  return (
    <span className="fc-tree-node-title">
      {isGate ? (
        <>
          <Tag color="processing" style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px', marginRight: 4 }}>
            {gateType || 'OR'}
          </Tag>
          <span>{title}</span>
        </>
      ) : (
        <span style={{ fontWeight: 500 }}>{title}</span>
      )}
      {description && (
        <span className="fc-tree-node-desc">（{description}）</span>
      )}
    </span>
  );
}

export default function FaultTreeCard({ tree, onSaveSuccess, onView }) {
  const [saving, setSaving] = useState(false);

  const treeData = useMemo(() => {
    const data = convertFaultTreeToTreeData(tree);
    // 为 antd Tree 添加 title 渲染
    const enrichNode = (node) => ({
      ...node,
      title: (
        <TreeNodeTitle
          title={node.title}
          description={node.description}
          isGate={node.isGate}
          gateType={node.gateType}
        />
      ),
      children: node.children?.map(enrichNode),
    });
    return data.map(enrichNode);
  }, [tree]);

  // 收集所有节点 key 用于默认全部展开
  const allKeys = useMemo(() => {
    const keys = [];
    const collect = (nodes) => {
      (nodes || []).forEach((n) => {
        keys.push(n.key);
        if (n.children) collect(n.children);
      });
    };
    collect(treeData);
    return keys;
  }, [treeData]);

  const handleSave = useCallback(async () => {
    if (!tree.id) return;
    setSaving(true);
    try {
      const treeNodes = (tree.nodes || []).map((n) => {
        if (n.node_type === 'gate') {
          return { id: n.id, node_type: 'gate', label: n.label || '', gate_type: n.gate_type || 'OR', remark: n.remark || '' };
        }
        return { id: n.id, node_type: 'event', label: n.label || '', remark: n.remark || '' };
      });
      const treeEdges = (tree.edges || []).map((e) => ({
        id: e.id, source_id: e.source_id, target_id: e.target_id,
      }));
      const payload = { name: tree.name || '未命名故障树', nodes: treeNodes, edges: treeEdges };

      const resp = await fetch(`/api/fault-trees/${encodeURIComponent(tree.id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (resp.ok) {
        message.success('故障树已保存');
        onSaveSuccess?.();
      } else {
        const err = await resp.json().catch(() => ({}));
        message.error(`保存失败: ${err.error || err.message || resp.status}`);
      }
    } catch (error) {
      message.error(`保存失败: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }, [tree, onSaveSuccess]);

  return (
    <div className="fc-fault-tree-card">
      <div className="fc-fault-tree-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ApartmentOutlined style={{ color: '#8e44ad' }} />
          <Text style={{ fontSize: 12, fontWeight: 600 }}>{tree.name || '未命名故障树'}</Text>
        </div>
        <div className="fc-fault-tree-actions">
          <Tooltip title={!tree.id ? '该故障树尚未保存到服务器' : '保存到服务器'}>
            <Button
              size="small"
              icon={<CloudUploadOutlined />}
              loading={saving}
              disabled={!tree.id}
              onClick={handleSave}
              style={{ borderRadius: 6, fontSize: 11 }}
            >
              保存
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* 树形结构 */}
      <div className="fc-fault-tree-body">
        <Tree
          treeData={treeData}
          defaultExpandAll
          expandedKeys={allKeys}
          selectable={false}
          showLine={{ showLeafIcon: false }}
          showIcon={false}
          style={{ fontSize: 12, background: 'transparent' }}
        />
      </div>

      {/* 底部「切换到故障树画布」按钮 */}
      <div className="fc-fault-tree-footer">
        <Button
          type="primary"
          icon={<BranchesOutlined />}
          onClick={() => onView?.(tree)}
          style={{ background: '#8e44ad', borderColor: '#8e44ad', borderRadius: 6, fontSize: 12 }}
        >
          在画布中查看故障树
        </Button>
      </div>
    </div>
  );
}
