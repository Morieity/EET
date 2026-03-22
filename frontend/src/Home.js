import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Home() {
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(false);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      color: '#333'
    }}>
      {/* 顶部导航栏 */}
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 50px',
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(10px)',
        boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            background: 'linear-gradient(45deg, #40b586, #28a745)', 
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold',
            fontSize: '20px'
          }}>
            F
          </div>
          <h2 style={{ margin: 0, fontSize: '24px', letterSpacing: '0.5px' }}>FlowMaster</h2>
        </div>
        
        <nav style={{ display: 'flex', gap: '20px' }}>
          <a href="#" style={{ color: '#555', textDecoration: 'none', fontWeight: '500' }}>首页</a>
          <a href="#" style={{ color: '#555', textDecoration: 'none', fontWeight: '500' }}>文档</a>
          <a href="#" style={{ color: '#555', textDecoration: 'none', fontWeight: '500' }}>关于</a>
        </nav>
      </header>

      {/* 页面主干 */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        textAlign: 'center'
      }}>
        
        {/* 欢迎区域 */}
        <div style={{
          background: 'white',
          padding: '60px 50px',
          borderRadius: '24px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.08)',
          maxWidth: '800px',
          width: '100%',
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* 背景装饰图形 */}
          <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '150px', height: '150px', background: 'rgba(64, 181, 134, 0.1)', borderRadius: '50%' }}></div>
          <div style={{ position: 'absolute', bottom: '-40px', left: '-40px', width: '100px', height: '100px', background: 'rgba(0, 123, 255, 0.05)', borderRadius: '50%' }}></div>

          <span style={{ 
            display: 'inline-block', 
            padding: '6px 14px', 
            background: '#e0f2f1', 
            color: '#00897b', 
            borderRadius: '20px', 
            fontSize: '14px',
            fontWeight: 'bold',
            marginBottom: '20px'
          }}>
            ✨ V 1.0 正式发布
          </span>
          
          <h1 style={{ 
            fontSize: '48px', 
            margin: '0 0 20px 0', 
            background: 'linear-gradient(to right, #2b5876 0%, #4e4376 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            构建你的思维流网络
          </h1>
          
          <p style={{ color: '#666', fontSize: '18px', lineHeight: '1.8', margin: '0 auto 40px', maxWidth: '600px' }}>
            无需复杂的设置，即可在此处通过直观的编辑器构建、组织并自动排版你的层级节点网络。
            将抽象灵感化为可视化图表，你的流程引擎从这里开启。
          </p>
          
          {/* 交互按钮 */}
          <button 
            onClick={() => navigate('/flow')}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{ 
              padding: '16px 40px', 
              fontSize: '20px', 
              fontWeight: 'bold',
              background: hovered ? '#34a071' : '#40b586', 
              color: 'white', 
              border: 'none', 
              borderRadius: '50px', 
              cursor: 'pointer',
              boxShadow: hovered ? '0 8px 25px rgba(64, 181, 134, 0.4)' : '0 4px 15px rgba(64, 181, 134, 0.3)',
              transform: hovered ? 'translateY(-3px)' : 'translateY(0)',
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              margin: '0 auto'
            }}
          >
            进入画板系统 <span style={{ transition: 'transform 0.3s', transform: hovered ? 'translateX(5px)' : 'translateX(0)' }}>👉</span>
          </button>
        </div>

        {/* 下方功能特性卡片展示区 */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          gap: '30px', 
          marginTop: '60px',
          flexWrap: 'wrap',
          maxWidth: '1000px'
        }}>
          {[
            { icon: '🎨', title: '全自由连线定制', desc: '自由修改节点的颜色与描述，双向绑定。' },
            { icon: '🌲', title: '智能树形拓扑结构', desc: '内置有向无环图(DAG)算法，一键整理纷乱节点。' },
            { icon: '🤖', title: 'AI 交互面板', desc: '悬浮智能机器助手，为你提供绘图建议操作。' }
          ].map((feature, idx) => (
            <div key={idx} style={{
              background: 'rgba(255,255,255,0.7)',
              backdropFilter: 'blur(5px)',
              padding: '25px',
              borderRadius: '16px',
              flex: '1 1 250px',
              minWidth: '250px',
              boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
              textAlign: 'left',
              transition: 'transform 0.3s',
            }}
             onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
             onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ fontSize: '32px', marginBottom: '15px' }}>{feature.icon}</div>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#333' }}>{feature.title}</h3>
              <p style={{ margin: 0, color: '#777', fontSize: '14px', lineHeight: '1.6' }}>{feature.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* 页脚 */}
      <footer style={{ 
        padding: '30px', 
        textAlign: 'center', 
        color: '#888', 
        fontSize: '14px',
        borderTop: '1px solid rgba(0,0,0,0.05)'
      }}>
        © 2026 FlowMaster. Built with React Flow & dagre.
      </footer>
    </div>
  );
}
