import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Typography, Card, Row, Col, Space, Tag } from 'antd';
import {
  RocketOutlined, ApartmentOutlined, BgColorsOutlined,
  RobotOutlined, FileTextOutlined, SafetyCertificateOutlined,
  ArrowRightOutlined, ThunderboltOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

export default function Home() {
  const navigate = useNavigate();
  const [hoveredCard, setHoveredCard] = useState(null);

  const features = [
    {
      icon: <BgColorsOutlined style={{ fontSize: 28, color: '#40b586' }} />,
      title: '自由画布编辑',
      desc: '拖拽节点、自由连线、自定义颜色与备注，所见即所得。',
      gradient: 'linear-gradient(135deg, #e0faf0 0%, #f0faf5 100%)',
    },
    {
      icon: <ApartmentOutlined style={{ fontSize: 28, color: '#3498db' }} />,
      title: '智能 DAG 排版',
      desc: '内置 dagre 有向无环图算法，一键将混乱节点整理为规范树形。',
      gradient: 'linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%)',
    },
    {
      icon: <RobotOutlined style={{ fontSize: 28, color: '#8e44ad' }} />,
      title: 'AI 故障诊断',
      desc: '多轮对话引导式诊断，RAG 知识增强，自动生成 IEC 61025 故障树。',
      gradient: 'linear-gradient(135deg, #f3e8ff 0%, #faf5ff 100%)',
    },
    {
      icon: <FileTextOutlined style={{ fontSize: 28, color: '#e67e22' }} />,
      title: '知识库管理',
      desc: '上传设备手册 PDF，三级语义去重，自动切片向量化入库。',
      gradient: 'linear-gradient(135deg, #fff8e8 0%, #fffcf0 100%)',
    },
    {
      icon: <SafetyCertificateOutlined style={{ fontSize: 28, color: '#e74c3c' }} />,
      title: '五种逻辑门',
      desc: '支持 AND / OR / XOR / INHIBIT / PRIORITY_AND 全部标准逻辑门。',
      gradient: 'linear-gradient(135deg, #ffe8e8 0%, #fff5f5 100%)',
    },
    {
      icon: <ThunderboltOutlined style={{ fontSize: 28, color: '#2ecc71' }} />,
      title: '导入导出保存',
      desc: 'JSON 导入导出、一键保存到服务器数据库，数据随时可恢复。',
      gradient: 'linear-gradient(135deg, #e8fff0 0%, #f0fff5 100%)',
    },
  ];

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(160deg, #f0f4f8 0%, #e8edf3 30%, #f5f0eb 60%, #eef3f0 100%)',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      {/* ===== 导航栏 ===== */}
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0 48px',
        height: 64,
        background: 'rgba(255,255,255,0.72)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(0,0,0,0.05)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, #40b586, #2ecc71)',
            borderRadius: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 700, fontSize: 16,
            boxShadow: '0 2px 8px rgba(64,181,134,0.3)',
          }}>
            FT
          </div>
          <Text strong style={{ fontSize: 18, color: '#1a1a2e', letterSpacing: 0.5 }}>EET Fault Tree</Text>
        </div>
        <Space size={24}>
          <Text type="secondary" style={{ cursor: 'pointer', fontSize: 14 }}>文档</Text>
          <Text type="secondary" style={{ cursor: 'pointer', fontSize: 14 }}>关于</Text>
        </Space>
      </header>

      {/* ===== Hero 区域 ===== */}
      <section style={{
        position: 'relative',
        overflow: 'hidden',
        padding: '100px 48px 80px',
        textAlign: 'center',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.6) 0%, rgba(235,242,248,0.5) 100%)',
      }}>
        {/* 装饰元素 */}
        <div style={{
          position: 'absolute', top: -120, right: '10%',
          width: 420, height: 420,
          background: 'radial-gradient(circle, rgba(64,181,134,0.12) 0%, transparent 65%)',
          borderRadius: '50%',
        }} />
        <div style={{
          position: 'absolute', bottom: -100, left: '3%',
          width: 360, height: 360,
          background: 'radial-gradient(circle, rgba(52,152,219,0.10) 0%, transparent 65%)',
          borderRadius: '50%',
        }} />
        <div style={{
          position: 'absolute', top: '15%', left: '12%',
          width: 220, height: 220,
          background: 'radial-gradient(circle, rgba(142,68,173,0.08) 0%, transparent 65%)',
          borderRadius: '50%',
        }} />
        <div style={{
          position: 'absolute', top: '60%', right: '8%',
          width: 180, height: 180,
          background: 'radial-gradient(circle, rgba(230,126,34,0.06) 0%, transparent 65%)',
          borderRadius: '50%',
        }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: 720, margin: '0 auto' }}>
          <Tag color="#40b586" style={{
            fontSize: 13, fontWeight: 600, padding: '4px 14px',
            borderRadius: 20, marginBottom: 24, border: 'none',
          }}>
            <RocketOutlined /> 智能故障诊断平台
          </Tag>

          <Title level={1} style={{
            fontSize: 52, fontWeight: 800, lineHeight: 1.2,
            margin: '0 0 20px',
            background: 'linear-gradient(135deg, #1a1a2e 0%, #40b586 50%, #3498db 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            构建智能故障树
            <br />
            诊断设备问题
          </Title>

          <Paragraph style={{
            fontSize: 17, color: '#666', lineHeight: 1.8,
            maxWidth: 560, margin: '0 auto 40px',
          }}>
            AI 驱动的多轮诊断对话，自动生成标准化故障树。
            上传设备手册构建知识库，让诊断更精准、更高效。
          </Paragraph>

          <Space size={16}>
            <Button
              type="primary"
              size="large"
              icon={<ArrowRightOutlined />}
              onClick={() => navigate('/flow')}
              style={{
                height: 52, padding: '0 36px',
                fontSize: 16, fontWeight: 600,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #40b586, #2ecc71)',
                border: 'none',
                boxShadow: '0 4px 16px rgba(64,181,134,0.35)',
              }}
            >
              进入工作台
            </Button>
            <Button
              size="large"
              onClick={() => navigate('/flow')}
              style={{
                height: 52, padding: '0 32px',
                fontSize: 16, fontWeight: 500,
                borderRadius: 12,
                borderColor: '#d9d9d9',
              }}
            >
              了解更多
            </Button>
          </Space>
        </div>
      </section>

      {/* ===== 功能特性 ===== */}
      <section style={{
        padding: '80px 48px',
        maxWidth: 1100,
        margin: '0 auto',
        position: 'relative',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <Text type="secondary" style={{ fontSize: 13, fontWeight: 600, letterSpacing: 2, textTransform: 'uppercase' }}>
            核心能力
          </Text>
          <Title level={2} style={{ margin: '8px 0 0', fontSize: 32, fontWeight: 700, color: '#1a1a2e' }}>
            全方位故障诊断工具链
          </Title>
        </div>

        <Row gutter={[24, 24]}>
          {features.map((f, idx) => (
            <Col xs={24} sm={12} lg={8} key={idx}>
              <Card
                bordered={false}
                hoverable
                onMouseEnter={() => setHoveredCard(idx)}
                onMouseLeave={() => setHoveredCard(null)}
                style={{
                  borderRadius: 16,
                  height: '100%',
                  background: hoveredCard === idx ? f.gradient : 'rgba(255,255,255,0.75)',
                  backdropFilter: 'blur(8px)',
                  boxShadow: hoveredCard === idx
                    ? '0 12px 36px rgba(0,0,0,0.10)'
                    : '0 2px 8px rgba(0,0,0,0.04)',
                  transition: 'all 0.35s ease',
                  border: hoveredCard === idx ? '1px solid rgba(64,181,134,0.15)' : '1px solid rgba(0,0,0,0.05)',
                  transform: hoveredCard === idx ? 'translateY(-4px)' : 'translateY(0)',
                }}
                bodyStyle={{ padding: 28 }}
              >
                <div style={{
                  width: 52, height: 52,
                  borderRadius: 14,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  marginBottom: 20,
                }}>
                  {f.icon}
                </div>
                <Text strong style={{ fontSize: 16, color: '#1a1a2e', display: 'block', marginBottom: 8 }}>
                  {f.title}
                </Text>
                <Text type="secondary" style={{ fontSize: 13, lineHeight: 1.7 }}>
                  {f.desc}
                </Text>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* ===== 底部 CTA ===== */}
      <section style={{
        padding: '64px 48px',
        textAlign: 'center',
        background: 'linear-gradient(135deg, rgba(64,181,134,0.05) 0%, rgba(52,152,219,0.05) 50%, rgba(142,68,173,0.04) 100%)',
        borderTop: '1px solid rgba(0,0,0,0.04)',
        borderBottom: '1px solid rgba(0,0,0,0.04)',
      }}>
        <Title level={3} style={{ margin: '0 0 12px', fontWeight: 700, color: '#1a1a2e' }}>
          准备好开始诊断了吗？
        </Title>
        <Text type="secondary" style={{ fontSize: 15, display: 'block', marginBottom: 28 }}>
          上传设备手册，描述故障现象，AI 帮你生成故障树。
        </Text>
        <Button
          type="primary"
          size="large"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate('/flow')}
          style={{
            height: 48, padding: '0 32px',
            fontSize: 15, fontWeight: 600,
            borderRadius: 10,
            background: '#40b586',
            border: 'none',
            boxShadow: '0 4px 12px rgba(64,181,134,0.3)',
          }}
        >
          立即开始
        </Button>
      </section>

      {/* ===== 页脚 ===== */}
      <footer style={{
        padding: '24px 48px',
        textAlign: 'center',
        background: 'rgba(255,255,255,0.5)',
      }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          © 2026 EET Fault Tree Platform — Built with React Flow, Ant Design & DeepSeek AI
        </Text>
      </footer>
    </div>
  );
}
