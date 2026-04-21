import { Button, Tooltip, Input, Space, Typography } from 'antd';
import {
  ArrowLeftOutlined, ImportOutlined, ExportOutlined, CloudUploadOutlined,
  ApartmentOutlined, PlusOutlined, ExperimentOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export default function FaultTreeToolbar({
  faultTreeId, faultTreeName, setFaultTreeName, saving,
  onBack, onTriggerImport, onDownloadJson, onLayout, onAddNode, onSaveToServer, onAiCheck,
}) {
  return (
    <div className="fc-tree-toolbar">
      <div className="fc-tree-toolbar-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Tooltip title="返回对话">
            <Button icon={<ArrowLeftOutlined />} onClick={onBack}>返回</Button>
          </Tooltip>
          {/* <ApartmentOutlined style={{ color: 'var(--fc-accent)', fontSize: 18 }} /> */}
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
            <Button size="small" icon={<ApartmentOutlined />} onClick={() => onLayout('LR')}>排版</Button>
          </Tooltip>
          <Tooltip title="添加事件节点">
            <Button size="small" icon={<PlusOutlined />} onClick={onAddNode}>添加节点</Button>
          </Tooltip>
          {onAiCheck && (
            <Tooltip title="AI 逻辑检查">
              <Button size="small" icon={<ExperimentOutlined />} onClick={onAiCheck}>AI检查</Button>
            </Tooltip>
          )}
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
  );
}
