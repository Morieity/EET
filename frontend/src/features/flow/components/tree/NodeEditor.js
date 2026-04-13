import { Button, Tooltip, Input, ColorPicker, Segmented, Typography } from 'antd';
import { NodeIndexOutlined, DeleteOutlined } from '@ant-design/icons';
import { gateButtons } from '../../utils/constants';

const { Text } = Typography;
const { TextArea } = Input;

export default function NodeEditor({ selectedNode, setNodes, variant, setVariant, onDeleteSelectedNode, onAddGate }) {
  return (
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
  );
}
