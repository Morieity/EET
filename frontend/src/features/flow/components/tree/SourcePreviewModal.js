import { Modal, Typography } from 'antd';

export function SourcePreviewModal({ source, open, onClose }) {
  return (
    <Modal
      title={`📄 ${source?.file_name || ''}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
    >
      <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
        {source?.page_content}
      </Typography.Paragraph>
    </Modal>
  );
}

export default SourcePreviewModal;
