import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { ReactFlowProvider, ReactFlow, applyNodeChanges, applyEdgeChanges, addEdge, Controls, Background, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { message } from 'antd';
import { getId, nodeTypes } from '../../utils/flowConfig';
import { getLayoutedElements } from '../../utils/layoutEngine';
import { convertFaultTreeToFlow } from '../../utils/faultTreeConverter';
import { updateFaultTree } from '../../services/faultTreeApi';
import FaultTreeToolbar from './FaultTreeToolbar';
import NodeEditor from './NodeEditor';
import '../../styles/tree.css';

function FaultTreeWorkspaceInner({ tree, onBack, onSendToChat }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;
  const edgesRef = useRef(edges);
  edgesRef.current = edges;
  const [variant, setVariant] = useState('cross');
  const [sidepanelCollapsed, setSidepanelCollapsed] = useState(false);
  const [faultTreeId, setFaultTreeId] = useState(null);
  const [faultTreeName, setFaultTreeName] = useState('');
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef(null);
  const flowWrapperRef = useRef(null);
  const onLayoutRef = useRef(null);

  const { screenToFlowPosition, toObject, setViewport, fitView } = useReactFlow();

  const applyLayout = useCallback((nextNodes, nextEdges, direction = 'LR') => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nextNodes, nextEdges, direction);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    window.requestAnimationFrame(() => {
      fitView({ padding: 0.2 });
    });
  }, [fitView]);

  const onLayout = useCallback((direction) => {
    applyLayout(nodes, edges, direction);
  }, [applyLayout, nodes, edges]);

  onLayoutRef.current = onLayout;

  useEffect(() => {
    if (!tree) return;
    const { nodes: ftNodes, edges: ftEdges } = convertFaultTreeToFlow(tree);
    applyLayout(ftNodes, ftEdges, 'LR');
    setFaultTreeId(tree.id || null);
    setFaultTreeName(tree.name || '未命名故障树');

    let frameId = null;
    let secondFrameId = null;

    frameId = window.requestAnimationFrame(() => {
      secondFrameId = window.requestAnimationFrame(() => {
        onLayoutRef.current?.('LR');
      });
    });

    return () => {
      if (frameId != null) window.cancelAnimationFrame(frameId);
      if (secondFrameId != null) window.cancelAnimationFrame(secondFrameId);
    };
  }, [tree, applyLayout]);

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
          sources: n.data?.sources || [],
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

      await updateFaultTree(faultTreeId, payload);
      message.success('故障树已保存');
    } catch (error) {
      message.error(`保存失败: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }, [faultTreeId, faultTreeName, toObject]);

  const onAddNode = useCallback(() => {
    const newNodeId = getId();
    const wrapperRect = flowWrapperRef.current?.getBoundingClientRect();
    const centerScreen = wrapperRect
      ? { x: wrapperRect.left + wrapperRect.width / 2, y: wrapperRect.top + wrapperRect.height / 2 }
      : { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    const centerFlow = screenToFlowPosition(centerScreen);

    // 在中心附近找一个不与已有节点重叠的位置
    const currentNodes = nodesRef.current;
    const NODE_W = 120;
    const NODE_H = 50;
    const STEP = 160;
    let position = centerFlow;
    for (let attempt = 0; attempt < 20; attempt++) {
      const angle = attempt * (Math.PI * 2 / 8);
      const radius = STEP * (Math.floor(attempt / 8) + 1);
      const candidate = attempt === 0
        ? centerFlow
        : { x: centerFlow.x + Math.cos(angle) * radius, y: centerFlow.y + Math.sin(angle) * radius };
      const overlaps = currentNodes.some(
        (n) => Math.abs((n.position?.x ?? 0) - candidate.x) < NODE_W && Math.abs((n.position?.y ?? 0) - candidate.y) < NODE_H,
      );
      if (!overlaps) { position = candidate; break; }
    }

    const newNode = {
      id: newNodeId,
      position,
      type: 'textUpdater',
      data: { label: `新事件节点`, remark: '' },
      style: { backgroundColor: '#40b586', color: 'white' },
      selected: false,
    };
    // 取消所有节点的选中状态，确保新节点以孤立方式加入（不触发自动连接）
    setNodes((snapshot) => snapshot.map((n) => ({ ...n, selected: false })).concat(newNode));
  }, [screenToFlowPosition]);

  const onDeleteSelectedNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((snapshot) => snapshot.filter((n) => n.id !== selectedNode.id));
    setEdges((snapshot) => snapshot.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
  }, [selectedNode]);

  const onAddGate = useCallback((gateType) => {
    const newNodeId = getId();
    const wrapperRect = flowWrapperRef.current?.getBoundingClientRect();
    const position = screenToFlowPosition(
      wrapperRect
        ? { x: wrapperRect.left + wrapperRect.width / 2, y: wrapperRect.top + wrapperRect.height / 2 }
        : { x: window.innerWidth / 2, y: window.innerHeight / 2 },
    );
    const newGateNode = {
      id: newNodeId,
      position,
      type: 'gate',
      data: { gateType },
    };

    setNodes((snapshot) => snapshot.concat(newGateNode));
  }, [screenToFlowPosition]);

  const toggleCollapse = useCallback((nodeId) => {
    const currentNodes = nodesRef.current;
    const currentEdges = edgesRef.current;
    const node = currentNodes.find(n => n.id === nodeId);
    const newCollapsed = !node?.data?.collapsed;

    const collapsedIds = new Set();
    currentNodes.forEach(n => {
      if (n.id === nodeId) {
        if (newCollapsed) collapsedIds.add(n.id);
      } else if (n.data?.collapsed) {
        collapsedIds.add(n.id);
      }
    });

    const hiddenIds = new Set();
    const addDescendants = (id, visited = new Set()) => {
      if (visited.has(id)) return;
      visited.add(id);
      currentEdges.filter(e => e.source === id).forEach(e => {
        hiddenIds.add(e.target);
        addDescendants(e.target, visited);
      });
    };
    collapsedIds.forEach(id => addDescendants(id));

    setNodes(prev => prev.map(n => ({
      ...n,
      data: n.id === nodeId ? { ...n.data, collapsed: newCollapsed } : n.data,
      hidden: hiddenIds.has(n.id),
    })));
  }, []);

  const enrichedNodes = useMemo(() => {
    const hasChildrenSet = new Set();
    edges.forEach(e => hasChildrenSet.add(e.source));
    return nodes.map(n => ({
      ...n,
      data: { ...n.data, hasChildren: hasChildrenSet.has(n.id), onToggleCollapse: toggleCollapse },
    }));
  }, [nodes, edges, toggleCollapse]);

  return (
    <div className="fc-tree-workspace">
      <input
        type="file"
        accept=".json"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={onFileChange}
      />

      <FaultTreeToolbar
        faultTreeId={faultTreeId}
        faultTreeName={faultTreeName}
        setFaultTreeName={setFaultTreeName}
        saving={saving}
        onBack={onBack}
        onTriggerImport={onTriggerImport}
        onDownloadJson={onDownloadJson}
        onLayout={onLayout}
        onAddNode={onAddNode}
        onSaveToServer={onSaveToServer}
        onAiCheck={onSendToChat ? () => onSendToChat('帮我检查当前故障树逻辑') : undefined}
      />

      <div className="fc-tree-body">
        <NodeEditor
          selectedNode={selectedNode}
          setNodes={setNodes}
          variant={variant}
          setVariant={setVariant}
          onDeleteSelectedNode={onDeleteSelectedNode}
          onAddGate={onAddGate}
          collapsed={sidepanelCollapsed}
          onToggleCollapse={() => setSidepanelCollapsed(v => !v)}
        />

        <div className="fc-tree-canvas" ref={flowWrapperRef}>
          <ReactFlow
            nodes={enrichedNodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Controls position="bottom-left" />
            <Background key={variant} color="#dbe5f0" variant={variant} />
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

