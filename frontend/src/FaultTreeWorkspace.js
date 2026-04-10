import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { ReactFlowProvider, ReactFlow, applyNodeChanges, applyEdgeChanges, addEdge, Controls, Background, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Button, Tooltip, Input, ColorPicker, Segmented, Typography, Space, message } from 'antd';
import {
  ArrowLeftOutlined, ImportOutlined, ExportOutlined, CloudUploadOutlined,
  ApartmentOutlined, PlusOutlined, NodeIndexOutlined, DeleteOutlined,
} from '@ant-design/icons';
import TextUpdaterNode from './TextUpdaterNode';
import GateNode from './GateNode';
import { getId, getLayoutedElements, convertFaultTreeToFlow } from './utils';
import './flow-chat.css';

const { Text } = Typography;
const { TextArea } = Input;

const nodeTypes = {
  textUpdater: TextUpdaterNode,
  gate: GateNode,
};

function FaultTreeWorkspaceInner({ tree, onBack }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [variant, setVariant] = useState('cross');
  const [faultTreeId, setFaultTreeId] = useState(null);
  const [faultTreeName, setFaultTreeName] = useState('');
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef(null);
  const flowWrapperRef = useRef(null);

  const { screenToFlowPosition, toObject, setViewport, fitView } = useReactFlow();

  useEffect(() => {
    if (!tree) return;
    const { nodes: ftNodes, edges: ftEdges } = convertFaultTreeToFlow(tree);
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(ftNodes, ftEdges, 'TB');
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    setFaultTreeId(tree.id || null);
    setFaultTreeName(tree.name || '未命名故障树');
    window.requestAnimationFrame(() => {
      fitView({ padding: 0.2 });
    });
  }, [tree, fitView]);

  const selectedNode = useMemo(() => nodes.find((n) => n.selected), [nodes]);

  const onNodesChange = useCallback(
    (changes) => setNodes((snapshot) => applyNodeChanges(changes, snapshot)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((snapshot) => applyEdgeChanges(changes, snapshot)),
    [],
  );
  const onConnect = useCallback(
    (params) => setEdges((snapshot) => addEdge({ ...params, type: 'smoothstep' }, snapshot)),
    [],
  );

  const onLayout = useCallback((direction) => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges, direction);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    window.requestAnimationFrame(() => {
      fitView({ padding: 0.2 });
    });
  }, [nodes, edges, fitView]);

  const onTriggerImport = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const onFileChange = useCallback((event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const flow = JSON.parse(e.target.result);
        setNodes(flow.nodes || []);
        setEdges(flow.edges || []);
        if (flow.viewport) {
          const { x = 0, y = 0, zoom = 1 } = flow.viewport;
          setViewport({ x, y, zoom });
        } else {
          window.requestAnimationFrame(() => {
            fitView({ padding: 0.2 });
          });
        }
        message.success('JSON 导入成功');
      } catch (err) {
        message.error('导入失败：JSON 文件格式错误');
        console.error(err);
      }
    };
    reader.readAsText(file);
    event.target.value = null;
  }, [setViewport, fitView]);

  const onDownloadJson = useCallback(() => {
    const flow = toObject();
    const jsonString = JSON.stringify(flow, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${faultTreeName || 'fault-tree'}-flow.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [toObject, faultTreeName]);

  const onSaveToServer = useCallback(async () => {
    if (!faultTreeId) {
      message.warning('当前故障树未关联服务器 ID，请先通过故障树库或 AI 生成后再保存');
      return;
    }

    setSaving(true);
    try {
      const flow = toObject();
      const treeNodes = (flow.nodes || []).map((n) => {
        if (n.type === 'gate') {
          return {
            id: n.id,
            node_type: 'gate',
            label: n.data?.label || '',
            gate_type: n.data?.gateType || 'OR',
            remark: n.data?.remark || '',
          };
        }
        return {
          id: n.id,
          node_type: 'event',
          label: n.data?.label || '',
          remark: n.data?.remark || '',
        };
      });

      const treeEdges = (flow.edges || []).map((e) => ({
        id: e.id,
        source_id: e.source,
        target_id: e.target,
      }));

      const payload = {
        name: faultTreeName || '未命名故障树',
        nodes: treeNodes,
        edges: treeEdges,
      };

      const resp = await fetch(`/api/fault-trees/${encodeURIComponent(faultTreeId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        message.success('故障树已保存');
      } else {
        const err = await resp.json().catch(() => ({}));
        message.error(`保存失败: ${err.error || err.message || resp.status}`);
      }
    } catch (error) {
      message.error(`保存失败: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }, [faultTreeId, faultTreeName, toObject]);

  const onAddNode = useCallback(() => {
    const newNodeId = getId();
    const wrapperRect = flowWrapperRef.current?.getBoundingClientRect();
    const position = screenToFlowPosition(
      wrapperRect
        ? { x: wrapperRect.left + wrapperRect.width / 2, y: wrapperRect.top + wrapperRect.height / 2 }
        : { x: window.innerWidth / 2, y: window.innerHeight / 2 },
    );

    const newNode = {
      id: newNodeId,
      position,
      type: 'textUpdater',
      data: { label: `Node ${newNodeId}`, remark: '' },
      style: { backgroundColor: '#40b586', color: 'white' },
    };
    setNodes((snapshot) => snapshot.concat(newNode));
  }, [screenToFlowPosition]);

  const onDeleteSelectedNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((snapshot) => snapshot.filter((n) => n.id !== selectedNode.id));
    setEdges((snapshot) => snapshot.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
  }, [selectedNode]);

  const onAddGate = useCallback((gateType) => {
    const parentNode = nodes.find((n) => n.selected);
    if (!parentNode) {
      message.warning('请先选择一个节点，再添加逻辑门');
      return;
    }

    const newNodeId = getId();
    const newGateNode = {
      id: newNodeId,
      position: {
        x: parentNode.position.x,
        y: parentNode.position.y + 150,
      },
      type: 'gate',
      data: { gateType },
    };
    const newEdge = {
      id: `${parentNode.id}-${newNodeId}`,
      source: parentNode.id,
      target: newNodeId,
      type: 'smoothstep',
    };

    setNodes((snapshot) => snapshot.concat(newGateNode));
    setEdges((snapshot) => snapshot.concat(newEdge));
  }, [nodes]);

  const gateButtons = [
    { type: 'AND', label: '& 与门', tip: 'AND Gate' },
    { type: 'OR', label: '≥1 或门', tip: 'OR Gate' },
    { type: 'XOR', label: '=1 异或', tip: 'XOR Gate' },
    { type: 'INHIBIT', label: '⊘ 禁止', tip: 'INHIBIT Gate' },
    { type: 'PRIORITY_AND', label: 'P& 优先', tip: 'PRIORITY AND Gate' },
  ];

  return (
    <div className="fc-tree-workspace">
      <input
        type="file"
        accept=".json"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={onFileChange}
      />

      <div className="fc-tree-toolbar">
        <div className="fc-tree-toolbar-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tooltip title="返回对话">
              <Button icon={<ArrowLeftOutlined />} onClick={onBack}>返回</Button>
            </Tooltip>
            <ApartmentOutlined style={{ color: 'var(--fc-accent)', fontSize: 18 }} />
            <Text strong style={{ fontSize: 15, color: 'var(--fc-text-primary)' }}>故障树查看与编辑</Text>
          </div>
          <Input
            size="small"
            value={faultTreeName}
            onChange={(e) => setFaultTreeName(e.target.value)}
            placeholder="故障树名称"
            style={{ width: 240 }}
          />
        </div>
        <div className="fc-tree-toolbar-actions">
          <Space size={6} wrap>
            <Tooltip title="导入 JSON 到画布">
              <Button size="small" icon={<ImportOutlined />} onClick={onTriggerImport}>导入</Button>
            </Tooltip>
            <Tooltip title="导出当前画布 JSON">
              <Button size="small" icon={<ExportOutlined />} onClick={onDownloadJson}>导出</Button>
            </Tooltip>
            <Tooltip title="自动排版为树形结构">
              <Button size="small" icon={<ApartmentOutlined />} onClick={() => onLayout('TB')}>排版</Button>
            </Tooltip>
            <Tooltip title="添加事件节点">
              <Button size="small" icon={<PlusOutlined />} onClick={onAddNode}>添加节点</Button>
            </Tooltip>
            <Tooltip title={faultTreeId ? '保存到服务器' : '该故障树没有服务器 ID，无法直接覆盖保存'}>
              <Button
                size="small"
                type="primary"
                icon={<CloudUploadOutlined />}
                loading={saving}
                onClick={onSaveToServer}
                style={{ background: 'var(--fc-accent)', borderColor: 'var(--fc-accent)' }}
              >
                保存
              </Button>
            </Tooltip>
          </Space>
        </div>
      </div>

      <div className="fc-tree-body">
        <div className="fc-tree-sidepanel">
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 11, marginBottom: 6, display: 'block' }}>画布背景</Text>
            <Segmented
              size="small"
              options={[
                { label: '空白', value: 'dots' },
                { label: '十字', value: 'lines' },
                { label: '点', value: 'cross' },
              ]}
              value={variant}
              onChange={setVariant}
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <NodeIndexOutlined style={{ fontSize: 14, color: 'var(--fc-accent)' }} />
              <Text strong style={{ fontSize: 13 }}>节点编辑</Text>
            </div>
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
              disabled={!selectedNode}
              onClick={onDeleteSelectedNode}
            >
              删除
            </Button>
          </div>

          {!selectedNode ? (
            <div className="fc-tree-empty-editor">
              <NodeIndexOutlined style={{ fontSize: 26, display: 'block', marginBottom: 8, color: '#d2d8df' }} />
              点击画布中的节点以编辑
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>添加逻辑门</Text>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {gateButtons.map((g) => (
                    <Tooltip title={g.tip} key={g.type}>
                      <Button size="small" onClick={() => onAddGate(g.type)} style={{ fontSize: 11, borderRadius: 6 }}>
                        {g.label}
                      </Button>
                    </Tooltip>
                  ))}
                </div>
              </div>

              <div>
                <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>标签</Text>
                <Input
                  size="small"
                  value={selectedNode.data?.label || ''}
                  onChange={(e) => {
                    const nextLabel = e.target.value;
                    setNodes((snapshot) => snapshot.map((n) => (
                      n.id === selectedNode.id
                        ? { ...n, data: { ...n.data, label: nextLabel } }
                        : n
                    )));
                  }}
                />
              </div>

              {selectedNode.type === 'textUpdater' && (
                <div>
                  <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>背景颜色</Text>
                  <ColorPicker
                    size="small"
                    value={selectedNode.style?.backgroundColor || '#40b586'}
                    onChange={(color) => {
                      const hex = color.toHexString();
                      setNodes((snapshot) => snapshot.map((n) => (
                        n.id === selectedNode.id
                          ? { ...n, style: { ...n.style, backgroundColor: hex } }
                          : n
                      )));
                    }}
                  />
                </div>
              )}

              {selectedNode.type === 'gate' && (
                <div>
                  <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>逻辑门类型</Text>
                  <Segmented
                    size="small"
                    options={gateButtons.map((g) => ({ label: g.type, value: g.type }))}
                    value={selectedNode.data?.gateType || 'OR'}
                    onChange={(value) => {
                      setNodes((snapshot) => snapshot.map((n) => (
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, gateType: value } }
                          : n
                      )));
                    }}
                    style={{ width: '100%' }}
                  />
                </div>
              )}

              <div>
                <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>备注</Text>
                <TextArea
                  size="small"
                  value={selectedNode.data?.remark || ''}
                  placeholder="输入节点备注..."
                  autoSize={{ minRows: 2, maxRows: 4 }}
                  onChange={(e) => {
                    const nextRemark = e.target.value;
                    setNodes((snapshot) => snapshot.map((n) => (
                      n.id === selectedNode.id
                        ? { ...n, data: { ...n.data, remark: nextRemark } }
                        : n
                    )));
                  }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="fc-tree-canvas" ref={flowWrapperRef}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Controls position="bottom-left" />
            <Background color="#dbe5f0" variant={variant} />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

export default function FaultTreeWorkspace(props) {
  return (
    <ReactFlowProvider>
      <FaultTreeWorkspaceInner {...props} />
    </ReactFlowProvider>
  );
}

