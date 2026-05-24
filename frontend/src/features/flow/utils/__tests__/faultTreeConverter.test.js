/**
 * Unit tests for faultTreeConverter helpers.
 * Pure functions — no DOM, no network.
 */
import {
  normalizeFaultTree,
  convertFaultTreeToTreeData,
  convertFaultTreeToFlow,
} from '../faultTreeConverter';

describe('normalizeFaultTree', () => {
  test('returns null for falsy / non-object input', () => {
    expect(normalizeFaultTree(null)).toBeNull();
    expect(normalizeFaultTree(undefined)).toBeNull();
    expect(normalizeFaultTree('string')).toBeNull();
  });

  test('passes through standard {nodes, edges} payload unchanged', () => {
    const tree = { name: 't', nodes: [{ id: 'n1' }], edges: [] };
    expect(normalizeFaultTree(tree)).toBe(tree);
  });

  test('unwraps payload nested under fault_tree key', () => {
    const inner = { nodes: [{ id: 'n1' }], edges: [] };
    expect(normalizeFaultTree({ fault_tree: inner })).toBe(inner);
  });

  test('converts LLM-style top_event + gates payload to standard form', () => {
    const llmPayload = {
      top_event: { id: 'TE', description: '系统失效' },
      gates: [{ id: 'G1', type: 'or', inputs: ['BE1', 'BE2'] }],
      basic_events: [
        { id: 'BE1', description: '泵失效' },
        { id: 'BE2', description: '阀失效' },
      ],
    };

    const result = normalizeFaultTree(llmPayload);

    expect(result).toBeTruthy();
    expect(result.name).toBe('系统失效');
    const ids = result.nodes.map((n) => n.id);
    expect(ids).toEqual(expect.arrayContaining(['TE', 'G1', 'BE1', 'BE2']));

    const gate = result.nodes.find((n) => n.id === 'G1');
    expect(gate.node_type).toBe('gate');
    expect(gate.gate_type).toBe('OR'); // upper-cased

    // top_event must connect to gate, gate must fan-out to its inputs
    expect(result.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ source_id: 'TE', target_id: 'G1' }),
        expect.objectContaining({ source_id: 'G1', target_id: 'BE1' }),
        expect.objectContaining({ source_id: 'G1', target_id: 'BE2' }),
      ])
    );
  });
});

describe('convertFaultTreeToTreeData', () => {
  test('builds antd Tree data with roots and children', () => {
    const tree = {
      nodes: [
        { id: 'TE', label: '顶事件', node_type: 'event' },
        { id: 'G1', label: '', node_type: 'gate', gate_type: 'AND' },
        { id: 'BE1', label: '泵失效', node_type: 'event', remark: '泵磨损' },
      ],
      edges: [
        { id: 'e1', source_id: 'TE', target_id: 'G1' },
        { id: 'e2', source_id: 'G1', target_id: 'BE1' },
      ],
    };

    const data = convertFaultTreeToTreeData(tree);

    expect(data).toHaveLength(1);
    const [root] = data;
    expect(root.key).toBe('TE');
    expect(root.title).toBe('顶事件');
    expect(root.children).toHaveLength(1);
    expect(root.children[0].key).toBe('G1');
    expect(root.children[0].isGate).toBe(true);
    expect(root.children[0].gateType).toBe('AND');
    expect(root.children[0].children[0].key).toBe('BE1');
    expect(root.children[0].children[0].description).toBe('泵磨损');
  });
});

describe('convertFaultTreeToFlow', () => {
  test('produces React Flow node/edge shapes and marks root in red', () => {
    const tree = {
      nodes: [
        { id: 'TE', label: '顶事件', node_type: 'event' },
        { id: 'G1', label: '', node_type: 'gate', gate_type: 'OR' },
        { id: 'BE1', label: '泵失效', node_type: 'event' },
      ],
      edges: [
        { id: 'e1', source_id: 'TE', target_id: 'G1' },
        { id: 'e2', source_id: 'G1', target_id: 'BE1' },
      ],
    };

    const { nodes, edges } = convertFaultTreeToFlow(tree);

    expect(nodes).toHaveLength(3);
    const te = nodes.find((n) => n.id === 'TE');
    const g1 = nodes.find((n) => n.id === 'G1');
    const be1 = nodes.find((n) => n.id === 'BE1');

    expect(te.type).toBe('textUpdater');
    expect(te.style.backgroundColor).toBe('#e74c3c'); // root color
    expect(be1.style.backgroundColor).toBe('#40b586'); // non-root color
    expect(g1.type).toBe('gate');
    expect(g1.data.gateType).toBe('OR');

    expect(edges).toEqual([
      { id: 'e1', source: 'TE', target: 'G1', type: 'smoothstep' },
      { id: 'e2', source: 'G1', target: 'BE1', type: 'smoothstep' },
    ]);
  });
});
