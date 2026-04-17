import { Handle, Position } from '@xyflow/react';

function TextUpdaterNode({ data, isConnectable, selected }) {
  return (
    <div className={`text-updater-node ${selected ? 'selected' : ''}`} style={{ padding: '10px', borderRadius: '5px', minWidth: '100px', textAlign: 'center', border: selected ? '2px solid #222' : '1px solid #777' }}>
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <div>
        {data.label}
      </div>
      <Handle type="source" position={Position.Right} id="a" isConnectable={isConnectable} />
    </div>
  );
}

export default TextUpdaterNode;

