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
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(ftNodes, ftEdges, 'LR');
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
      />

      <div className="fc-tree-body">
        <NodeEditor
          selectedNode={selectedNode}
          setNodes={setNodes}
          variant={variant}
          setVariant={setVariant}
          onDeleteSelectedNode={onDeleteSelectedNode}
          onAddGate={onAddGate}
        />

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

