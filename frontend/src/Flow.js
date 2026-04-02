import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactFlow, applyNodeChanges, applyEdgeChanges, addEdge, Controls, Background, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Button, Tooltip, Divider, Input, ColorPicker, Segmented, Typography, Space } from 'antd';
import {
  HomeOutlined, ImportOutlined, ExportOutlined, CloudUploadOutlined,
  ApartmentOutlined, PlusOutlined, NodeIndexOutlined,
} from '@ant-design/icons';
import AiChatPanel from './AiChatPanel';
import DocumentUploadPanel from './DocumentUploadPanel';
import TextUpdaterNode from './TextUpdaterNode';
import GateNode from './GateNode';
import { initialNodes, initialEdges } from './initialElements';
import { getId, getLayoutedElements, convertFaultTreeToFlow } from './utils';

const { Text } = Typography;
const { TextArea } = Input;

const nodeTypes = { 
  textUpdater: TextUpdaterNode,
  gate: GateNode
};

export default function Flow() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [variant, setVariant] = useState('cross');
  const [faultTreeId, setFaultTreeId] = useState(null);
  
  const fileInputRef = useRef(null);
  const { screenToFlowPosition, toObject, setViewport, fitView } = useReactFlow();

  // 接收 AI 诊断生成的故障树并渲染到画布
  const handleFaultTreeGenerated = useCallback((faultTree) => {
    const { nodes: ftNodes, edges: ftEdges } = convertFaultTreeToFlow(faultTree);
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(ftNodes, ftEdges, 'TB');
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    setFaultTreeId(faultTree.id || null);
    window.requestAnimationFrame(() => { fitView(); });
  }, [setNodes, setEdges, fitView]);

  const onLayout = useCallback(
    (direction) => {
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        nodes,
        edges,
        direction
      );

      setNodes([...layoutedNodes]);
      setEdges([...layoutedEdges]);

      // 稍微延迟让 React Flow 渲染出新位置后再将画面居中
      window.requestAnimationFrame(() => {
        fitView();
      });
    },
    [nodes, edges, setNodes, setEdges, fitView]
  );

  // 触发本地文件选择
  const onTriggerImport = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, []);

  // 处理文件读取并重建视图
  const onFileChange = useCallback((event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const flow = JSON.parse(e.target.result);
        
        if (flow) {
          // 恢复节点和连线数据
          setNodes(flow.nodes || []);
          setEdges(flow.edges || []);
          
          // 恢复画布缩放和平移位置
          if (flow.viewport) {
            const { x = 0, y = 0, zoom = 1 } = flow.viewport;
            setViewport({ x, y, zoom });
          }
        }
      } catch (err) {
        alert('导入的 JSON 文件格式解析错误！');
        console.error(err);
      }
    };
    reader.readAsText(file);
    
    // 清空 input 值，允许用户以后重复上传同名文件
    event.target.value = null;
  }, [setNodes, setEdges, setViewport]);

  const onDownloadJson = useCallback(() => {
    // 1. 获取包含 nodes、edges 和 viewport 的完整数据对象
    const flow = toObject();
    
    // 2. 将数据转换为 JSON 字符串并创建 Blob
    const jsonString = JSON.stringify(flow, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    // 3. 构建临时链接触发下载
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'flow-data.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [toObject]);

  const onSaveToServer = useCallback(async () => {
    const flow = toObject();

    // 将 React Flow 节点/边转换为后端故障树格式
    const treeNodes = flow.nodes.map((n) => {
      const d = { ...n.data };
      // 移除前端专用字段
      delete d.label;
      delete d.remark;
      delete d.gateType;
      if (n.type === 'textUpdater' || n.type === 'event') {
        return { id: n.id, type: 'event', data: { label: n.data.label || '', ...(n.data.remark ? { remark: n.data.remark } : {}) } };
      }
      if (n.type === 'gate') {
        return { id: n.id, type: 'gate', data: { gateType: n.data.gateType || 'OR' } };
      }
      return { id: n.id, type: n.type, data: n.data };
    });

    const treeEdges = flow.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
    }));

    const payload = { nodes: treeNodes, edges: treeEdges };

    if (faultTreeId) {
      // 保存到已有故障树
      try {
        const resp = await fetch(`/api/fault-trees/${encodeURIComponent(faultTreeId)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (resp.ok) {
          alert('故障树已保存到服务器！');
        } else {
          const err = await resp.json().catch(() => ({}));
          alert(`保存失败: ${err.message || resp.status}`);
        }
      } catch (error) {
        alert(`保存失败: ${error.message}`);
      }
    } else {
      // 没有关联故障树时，导出到控制台并提示
      console.log('故障树数据 (无关联ID):', payload);
      alert('当前画布未关联诊断会话的故障树。\n请先通过 AI 诊断生成故障树，然后再保存。');
    }
  }, [toObject, faultTreeId]);

  const onNodesChange = useCallback(
    (changes) => setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    [],
  );
  const onConnect = useCallback(
    (params) => setEdges((edgesSnapshot) => addEdge({ ...params, type: 'smoothstep' }, edgesSnapshot)),
    [],
  );

  const onAddNode = useCallback(() => {
    const newNodeId = getId();
    
    // 生成一个距离中心不远的默认位置
    const position = screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
    });

    const newNode = {
      id: newNodeId,
      position,
      type: 'textUpdater',
      data: { label: `Node ${newNodeId}` },
      style: { backgroundColor: '#40b586', color: 'white' }
    };

    setNodes((nds) => nds.concat(newNode));
  }, [screenToFlowPosition, setNodes]);

  const onAddGate = useCallback((gateType) => {
    const selectedNode = nodes.find((n) => n.selected);
    if (!selectedNode) {
      alert('Select a node first');
      return;
    }

    const newNodeId = getId();
    const position = {
      x: selectedNode.position.x,
      y: selectedNode.position.y + 150,
    };

    const newGateNode = {
      id: newNodeId,
      position,
      type: 'gate',
      data: { gateType },
    };

    const newEdge = {
      id: `${selectedNode.id}-${newNodeId}`,
      source: selectedNode.id,
      target: newNodeId,
      type: 'smoothstep',
    };

    setNodes((nds) => nds.concat(newGateNode));
    setEdges((eds) => eds.concat(newEdge));
  }, [nodes, setNodes, setEdges]);

  const selectedNode = nodes.find(n => n.selected);

  // 逻辑门配置
  const gateButtons = [
    { type: 'AND', label: '& 与门', tip: 'AND Gate' },
    { type: 'OR', label: '≥1 或门', tip: 'OR Gate' },
    { type: 'XOR', label: '=1 异或', tip: 'XOR Gate' },
    { type: 'INHIBIT', label: '⊘ 禁止', tip: 'INHIBIT Gate' },
    { type: 'PRIORITY_AND', label: 'P& 优先', tip: 'PRIORITY AND Gate' },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#f0f2f5', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* ========== 左侧面板 (25%) ========== */}
      <div style={{
        width: '25%',
        minWidth: 280,
        maxWidth: 360,
        display: 'flex',
        flexDirection: 'column',
        background: '#fff',
        borderRight: '1px solid #e8e8e8',
        overflow: 'hidden',
      }}>
        {/* 顶部 Logo / 导航 */}
        <div style={{
          padding: '14px 16px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApartmentOutlined style={{ fontSize: 18, color: '#40b586' }} />
            <Text strong style={{ fontSize: 15, color: '#1a1a2e' }}>故障树编辑器</Text>
          </div>
          <Tooltip title="返回首页">
            <Button type="text" icon={<HomeOutlined />} onClick={() => navigate('/')} />
          </Tooltip>
        </div>

        {/* 工具栏 */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Space size={6} wrap>
            <Tooltip title="导入 JSON">
              <Button size="small" icon={<ImportOutlined />} onClick={onTriggerImport}>导入</Button>
            </Tooltip>
            <input type="file" accept=".json" ref={fileInputRef} style={{ display: 'none' }} onChange={onFileChange} />
            <Tooltip title="导出 JSON">
              <Button size="small" icon={<ExportOutlined />} onClick={onDownloadJson}>导出</Button>
            </Tooltip>
            <Tooltip title="保存到服务器">
              <Button size="small" type="primary" icon={<CloudUploadOutlined />} onClick={onSaveToServer}
                style={{ background: '#40b586', borderColor: '#40b586' }}>保存</Button>
            </Tooltip>
            <Tooltip title="自动排版为树形结构">
              <Button size="small" icon={<ApartmentOutlined />} onClick={() => onLayout('TB')}>排版</Button>
            </Tooltip>
          </Space>
        </div>

        {/* 背景样式 */}
        <div style={{ padding: '10px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Text type="secondary" style={{ fontSize: 11, marginBottom: 6, display: 'block' }}>画布背景</Text>
          <Segmented
            size="small"
            options={[
              { label: '点', value: 'dots' },
              { label: '线', value: 'lines' },
              { label: '十字', value: 'cross' },
            ]}
            value={variant}
            onChange={setVariant}
            style={{ width: '100%' }}
          />
        </div>

        {/* Node Editor 区域 */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <div style={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <NodeIndexOutlined style={{ fontSize: 14, color: '#40b586' }} />
                <Text strong style={{ fontSize: 13 }}>节点编辑</Text>
              </div>
              <Button type="primary" size="small" icon={<PlusOutlined />} onClick={onAddNode}
                style={{ background: '#40b586', borderColor: '#40b586', borderRadius: 6, fontSize: 12 }}>
                添加节点
              </Button>
            </div>

            {!selectedNode ? (
              <div style={{
                padding: '24px 16px',
                textAlign: 'center',
                color: '#bbb',
                fontSize: 13,
                background: '#fafbfc',
                borderRadius: 8,
                border: '1px dashed #e8e8e8',
              }}>
                <NodeIndexOutlined style={{ fontSize: 28, display: 'block', marginBottom: 8, color: '#ddd' }} />
                点击画布中的节点以编辑
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* 逻辑门按钮 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 11, marginBottom: 6, display: 'block' }}>添加逻辑门</Text>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {gateButtons.map(g => (
                      <Tooltip title={g.tip} key={g.type}>
                        <Button size="small" onClick={() => onAddGate(g.type)}
                          style={{ fontSize: 11, borderRadius: 6 }}>
                          {g.label}
                        </Button>
                      </Tooltip>
                    ))}
                  </div>
                </div>

                {/* 标签输入 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>标签</Text>
                  <Input
                    size="small"
                    value={selectedNode.data.label || ''}
                    onChange={(e) => {
                      setNodes(nds => nds.map(n =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, label: e.target.value } }
                          : n
                      ));
                    }}
                    style={{ borderRadius: 6 }}
                  />
                </div>

                {/* 颜色选择 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>背景颜色</Text>
                  <ColorPicker
                    size="small"
                    value={selectedNode.style?.backgroundColor || '#40b586'}
                    onChange={(color) => {
                      setNodes(nds => nds.map(n =>
                        n.id === selectedNode.id
                          ? { ...n, style: { ...n.style, backgroundColor: color.toHexString() } }
                          : n
                      ));
                    }}
                  />
                </div>

                {/* 备注 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>备注</Text>
                  <TextArea
                    size="small"
                    value={selectedNode.data.remark || ''}
                    placeholder="输入节点备注..."
                    autoSize={{ minRows: 2, maxRows: 4 }}
                    onChange={(e) => {
                      setNodes(nds => nds.map(n =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, remark: e.target.value } }
                          : n
                      ));
                    }}
                    style={{ borderRadius: 6, fontSize: 12 }}
                  />
                </div>
              </div>
            )}
          </div>

          <Divider style={{ margin: '4px 0' }} />

          {/* 文档上传区域 */}
          <DocumentUploadPanel />
        </div>
      </div>

      {/* ========== 中间画布 (50%) ========== */}
      <div style={{ flex: 1, position: 'relative' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onConnect={onConnect}
          fitView
        >
          <Controls position="bottom-left" style={{ marginBottom: 10, marginLeft: 10 }} />
          <Background color="skyblue" variant={variant} />
        </ReactFlow>
      </div>

      {/* ========== 右侧 AI 面板 (25%) ========== */}
      <div style={{
        width: '25%',
        minWidth: 300,
        maxWidth: 400,
        borderLeft: '1px solid #e8e8e8',
        background: '#fff',
        overflow: 'hidden',
      }}>
        <AiChatPanel onFaultTreeGenerated={handleFaultTreeGenerated} />
      </div>
    </div>
  );
}
