import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactFlow, applyNodeChanges, applyEdgeChanges, addEdge, Controls, Background, Panel, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import AiChatPanel from './AiChatPanel';
import DocumentUploadPanel from './DocumentUploadPanel';
import TextUpdaterNode from './TextUpdaterNode';
import GateNode from './GateNode';
import { initialNodes, initialEdges } from './initialElements';
import { getId, getLayoutedElements, convertFaultTreeToFlow } from './utils';

const nodeTypes = { 
  textUpdater: TextUpdaterNode,
  gate: GateNode
};

export default function Flow() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [variant, setVariant] = useState('cross');
  const [isPanelOpen, setIsPanelOpen] = useState(true);
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

  return (
    <>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onConnect={onConnect}
        fitView
      >
        <Controls />
        <Background color='skyblue' variant={variant} />
        <Panel position="bottom-left" style={{ background: '#f8f8f8', padding: '10px', borderRadius: '8px', border: '1px solid #ccc' }}>
          <div style={{ marginBottom: '5px', fontWeight: 'bold' }}>画布变体 (Variant):</div>
          <button onClick={() => setVariant('dots')} style={{ marginRight: '5px' }}>Dots</button>
          <button onClick={() => setVariant('lines')} style={{ marginRight: '5px' }}>Lines</button>
          <button onClick={() => setVariant('cross')}>Cross</button>
        </Panel>
        
        {/* 新增：左上角的功能面板组合 */}
        <Panel position="top-left" style={{ display: 'flex', flexDirection: 'row', alignItems: 'flex-start', gap: '10px' }}>
          {/* 主体折叠区域 */}
          <div style={{ 
            display: isPanelOpen ? 'flex' : 'none', 
            flexDirection: 'column', 
            gap: '10px'
          }}>
            {/* 保存与导出按钮组作为第一部分（在上面） */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                onClick={onTriggerImport} 
                style={{ padding: '8px 12px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', flex: 1 }}
              >
                📤 导入 JSON
              </button>
              {/* 隐藏的文件上传 input */}
              <input 
                type="file" 
                accept=".json" 
                ref={fileInputRef} 
                style={{ display: 'none' }} 
                onChange={onFileChange} 
              />
              <button 
                onClick={onDownloadJson} 
                style={{ padding: '8px 12px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', flex: 1 }}
              >
                📥 导出 JSON
              </button>
              <button 
                onClick={onSaveToServer} 
                style={{ padding: '8px 12px', background: '#40b586', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', flex: 1 }}
              >
                ☁️ 保存到数据库
              </button>
              <button 
                onClick={() => onLayout('TB')} 
                style={{ padding: '8px 12px', background: '#e0f7fa', color: '#333', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', flex: 1 }}
                title="自动将混乱的节点排列为规范的上下树形结构"
              >
                🌲 自动排版
              </button>
            </div>

            <button
              onClick={() => navigate('/')}
              style={{ padding: '8px 12px', background: '#333', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
              title="返回主页"
            >
              🏠 返回首页
            </button>

            {/* 选中节点的编辑面板作为第二部分（在下面） */}
            <div style={{ background: '#f8f8f8', padding: '10px', borderRadius: '8px', border: '1px solid #ccc' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4 style={{ margin: 0 }}>Node Editor</h4>
                <button 
                  onClick={onAddNode} 
                  style={{ padding: '4px 8px', background: '#40b586', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                >
                  ➕ 添加节点
                </button>
              </div>
              {(() => {
                const selectedNode = nodes.find(n => n.selected);
                if (!selectedNode) return <p style={{ margin: 0 }}>No node selected</p>;

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ marginBottom: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button 
                        onClick={() => onAddGate('AND')} 
                        style={{ padding: '4px 8px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center' }}
                      >
                       ➕ &amp; 与门
                      </button>
                      <button 
                        onClick={() => onAddGate('OR')} 
                        style={{ padding: '4px 8px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center' }}
                      >
                       ➕ ≥1 或门
                      </button>
                      <button 
                        onClick={() => onAddGate('XOR')} 
                        style={{ padding: '4px 8px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center' }}
                      >
                       ➕ =1 异或门
                      </button>
                      <button 
                        onClick={() => onAddGate('INHIBIT')} 
                        style={{ padding: '4px 8px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center' }}
                      >
                       ➕ ⊘ 禁止门
                      </button>
                      <button 
                        onClick={() => onAddGate('PRIORITY_AND')} 
                        style={{ padding: '4px 8px', background: '#fff', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center' }}
                      >
                       ➕ P&amp; 优先与门
                      </button>
                    </div>
                    <label>
                      Label:
                      <input 
                        type="text" 
                        value={selectedNode.data.label || ''} 
                        onChange={(e) => {
                          setNodes(nds => nds.map(n => 
                            n.id === selectedNode.id 
                              ? { ...n, data: { ...n.data, label: e.target.value } } 
                              : n
                          ));
                        }}
                        style={{ marginLeft: '5px' }}
                      />
                    </label>
                    <label>
                      Background Color:
                      <input 
                        type="color" 
                        value={selectedNode.style?.backgroundColor || '#ffffff'} 
                        onChange={(e) => {
                          setNodes(nds => nds.map(n => 
                            n.id === selectedNode.id 
                              ? { ...n, style: { ...n.style, backgroundColor: e.target.value } } 
                              : n
                          ));
                        }}
                        style={{ marginLeft: '5px' }}
                      />
                    </label>
                    <label style={{ display: 'flex', flexDirection: 'column' }}>
                      Remark (备注):
                      <textarea 
                        value={selectedNode.data.remark || ''} 
                        placeholder="在这里输入节点备注..."
                        onChange={(e) => {
                          setNodes(nds => nds.map(n => 
                            n.id === selectedNode.id 
                              ? { ...n, data: { ...n.data, remark: e.target.value } } 
                              : n
                          ));
                        }}
                        style={{ marginTop: '5px', minHeight: '60px', resize: 'vertical', padding: '4px' }}
                      />
                    </label>
                  </div>
                );
              })()}
            </div>
          </div>
          
          {/* 折叠/展开控制按钮（在整个面板的最右侧） */}
          <button
            onClick={() => setIsPanelOpen(!isPanelOpen)}
            style={{
              padding: '8px 12px',
              background: '#fff',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
              height: 'fit-content'
            }}
            title={isPanelOpen ? "收起面板" : "展开面板"}
          >
            {isPanelOpen ? '◀' : '▶'}
          </button>
        </Panel>

        <AiChatPanel onFaultTreeGenerated={handleFaultTreeGenerated} />

        <DocumentUploadPanel />


      </ReactFlow>
    </>
  );
}
