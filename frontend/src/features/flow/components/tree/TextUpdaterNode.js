import { Handle, Position } from '@xyflow/react';

function TextUpdaterNode({ data, isConnectable, selected }) {
  const sourceCount = data.sources?.length || 0;

  return (
    <div className={`text-updater-node ${selected ? 'selected' : ''}`} style={{ position: 'relative', padding: '10px', borderRadius: '5px', minWidth: '100px', textAlign: 'center', border: selected ? '2px solid #222' : '1px solid #777' }}>
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <div>
        {data.label}
      </div>
      {sourceCount > 0 && (
        <div style={{
          position: 'absolute',
          bottom: 2,
          right: 4,
          fontSize: 10,
          color: '#1890ff',
          opacity: 0.8,
          pointerEvents: 'none',
        }}>
          {sourceCount}📄
        </div>
      )}
      <Handle type="source" position={Position.Right} id="a" isConnectable={isConnectable} />
    </div>
  );
}

export default TextUpdaterNode;

