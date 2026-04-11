/**
 * 将 LLM 输出的 fault_tree 格式 (top_event/gates/basic_events)
 * 转换为标准后端格式 { name, nodes, edges }。
 */
function convertLLMFormatToStandard(raw) {
  const nodes = [];
  const edges = [];
  let edgeId = 0;

  const topEvent = raw.top_event;
  const gates = raw.gates || [];
  const basicEvents = raw.basic_events || raw.events || [];
  const gateIds = new Set(gates.map((g) => g.id));

  if (topEvent) {
    nodes.push({
      id: topEvent.id,
      node_type: 'event',
      label: topEvent.description || topEvent.label || topEvent.id,
      remark: '',
    });
    if (!gateIds.has(topEvent.id) && gates.length > 0) {
      edges.push({ id: `e-${edgeId++}`, source_id: topEvent.id, target_id: gates[0].id });
    }
  }

  gates.forEach((g) => {
    const existing = nodes.find((n) => n.id === g.id);
    if (existing) {
      existing.node_type = 'gate';
      existing.gate_type = (g.type || g.gate_type || 'OR').toUpperCase();
    } else {
      nodes.push({
        id: g.id,
        node_type: 'gate',
        label: g.description || g.label || g.id,
        gate_type: (g.type || g.gate_type || 'OR').toUpperCase(),
        remark: '',
      });
    }
    (g.inputs || []).forEach((inputId) => {
      edges.push({ id: `e-${edgeId++}`, source_id: g.id, target_id: inputId });
    });
  });

  basicEvents.forEach((ev) => {
    if (!nodes.find((n) => n.id === ev.id)) {
      nodes.push({
        id: ev.id,
        node_type: 'event',
        label: ev.description || ev.label || ev.id,
        remark: ev.remark || '',
      });
    }
  });

  edges.forEach((e) => {
    if (!nodes.find((n) => n.id === e.target_id)) {
      nodes.push({ id: e.target_id, node_type: 'event', label: e.target_id, remark: '' });
    }
  });

  return { name: raw.name || topEvent?.description || '故障树分析', nodes, edges };
}

/**
 * 尝试将任意 JSON 对象标准化为 { name, nodes, edges } 格式。
 */
export function normalizeFaultTree(obj) {
  if (!obj || typeof obj !== 'object') return null;
  const raw = obj.fault_tree || obj;
  if (Array.isArray(raw.nodes) && Array.isArray(raw.edges)) return raw;
  if (raw.top_event || raw.gates) return convertLLMFormatToStandard(raw);
  return null;
}

/**
 * 将后端故障树 nodes/edges 转换为 antd Tree 的 treeData 格式。
 */
export const convertFaultTreeToTreeData = (faultTree) => {
  const rawNodes = faultTree.nodes || [];
  const rawEdges = faultTree.edges || [];

  const nodeMap = {};
  rawNodes.forEach((n) => { nodeMap[n.id] = n; });

  const childrenMap = {};
  const hasIncoming = new Set();
  rawEdges.forEach((e) => {
    const src = e.source_id || e.source;
    const tgt = e.target_id || e.target;
    if (!childrenMap[src]) childrenMap[src] = [];
    childrenMap[src].push(tgt);
    hasIncoming.add(tgt);
  });

  const roots = rawNodes.filter((n) => !hasIncoming.has(n.id));

  const buildTree = (nodeId) => {
    const n = nodeMap[nodeId];
    if (!n) return null;
    const isGate = n.node_type === 'gate';
    const label = n.label || n.id;
    const desc = isGate ? (n.gate_type || 'OR') : (n.remark || '');
    const children = (childrenMap[nodeId] || []).map(buildTree).filter(Boolean);
    return {
      key: n.id,
      title: label,
      description: desc,
      isGate,
      gateType: isGate ? (n.gate_type || 'OR') : undefined,
      children: children.length ? children : undefined,
    };
  };

  return roots.map((r) => buildTree(r.id)).filter(Boolean);
};

/**
 * 将后端故障树数据转换为 React Flow 节点和边
 */
export const convertFaultTreeToFlow = (faultTree) => {
  const rawNodes = faultTree.nodes || [];
  const rawEdges = faultTree.edges || [];

  const hasIncoming = new Set(rawEdges.map(e => e.target_id));

  const nodes = rawNodes.map((n, index) => {
    if (n.node_type === 'gate') {
      return {
        id: n.id,
        type: 'gate',
        position: { x: 0, y: index * 100 },
        data: {
          gateType: n.gate_type || 'OR',
          label: n.label || '',
        },
      };
    }
    const isRoot = !hasIncoming.has(n.id);
    return {
      id: n.id,
      type: 'textUpdater',
      position: { x: 0, y: index * 100 },
      data: {
        label: n.label || n.id,
        remark: n.remark || '',
      },
      style: {
        backgroundColor: isRoot ? '#e74c3c' : '#40b586',
        color: 'white',
      },
    };
  });

  const edges = rawEdges.map((e) => ({
    id: e.id,
    source: e.source_id,
    target: e.target_id,
    type: 'smoothstep',
  }));

  return { nodes, edges };
};
