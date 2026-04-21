import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Network, Shield, Zap, GitBranch, TrendingUp, Users, Award, Sparkles, Code, FileJson, BookOpen, Brain } from 'lucide-react';
import { Button } from '../../ui/button';
import { Card } from '../../ui/card';
import { motion } from 'motion/react';

const SECTION_LABELS = ['首页', '数据', '功能', '应用', '文档', '团队', '关于'];
const SCROLL_COOLDOWN = 100;

export default function Home() {
  const [currentSection, setCurrentSection] = useState(0);
  const [viewH, setViewH] = useState(() => window.innerHeight);
  const isScrolling = useRef(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const updateVh = () => setViewH(window.innerHeight);
    window.addEventListener('resize', updateVh);
    return () => window.removeEventListener('resize', updateVh);
  }, []);

  const totalSections = SECTION_LABELS.length;

  const scrollToSection = useCallback((index) => {
    if (index < 0 || index >= totalSections || isScrolling.current) return;
    isScrolling.current = true;
    setCurrentSection(index);
    setTimeout(() => { isScrolling.current = false; }, SCROLL_COOLDOWN);
  }, [totalSections]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e) => {
      e.preventDefault();
      if (isScrolling.current) return;
      const direction = e.deltaY > 0 ? 1 : -1;
      scrollToSection(currentSection + direction);
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [currentSection, scrollToSection]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault();
        scrollToSection(currentSection + 1);
      } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault();
        scrollToSection(currentSection - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentSection, scrollToSection]);

  const stats = [
    { label: '代码行数', value: '38352', icon: Users },
    { label: '参考文献', value: '20+', icon: GitBranch },
    { label: '分析准确率', value: '99.9%', icon: Award },
    { label: '响应时间', value: '30-60s', icon: TrendingUp },
  ];

  const features = [
    {
      icon: Network,
      title: '可视化编辑器',
      description: '直观的拖放界面，轻松构建复杂故障树。添加门、事件和连接，一切尽在掌握。',
      color: 'green',
      gradient: 'from-[#A9D098] to-[#4C9755]',
    },
    {
      icon: Shield,
      title: '安全性分析',
      description: '行业标准符号和门类型，包括AND、OR和事件节点。完美适用于安全关键系统。',
      color: 'green',
      gradient: 'from-green-500 to-emerald-500',
    },
    {
      icon: Zap,
      title: '导出与分享',
      description: '将故障树导出为JSON格式，便于协作和文档记录。导入现有树继续工作。',
      color: 'green',
      gradient: 'from-[#A9D098] to-[#4C9755]',
    },
    {
      icon: Code,
      title: '实时协作',
      description: '与团队成员实时协作，共同构建和分析故障树。即时同步所有更改。',
      color: 'orange',
      gradient: 'from-orange-500 to-red-500',
    },
    {
      icon: FileJson,
      title: '数据导入导出',
      description: '支持多种格式的数据导入导出，与现有工具无缝集成，提高工作效率。',
      color: 'green',
      gradient: 'from-[#A9D098] to-[#4C9755]',
    },
    {
      icon: Sparkles,
      title: 'AI 智能建议',
      description: '智能分析系统，自动识别潜在风险点，提供优化建议，提升分析质量。',
      color: 'yellow',
      gradient: 'from-yellow-500 to-amber-500',
    },
  ];

  return (
    <div ref={containerRef} className="bg-white overflow-hidden relative" style={{ height: viewH }}>
      {/* Side Navigation Indicator */}
      <nav className="fixed right-6 top-1/2 -translate-y-1/2 z-50 flex flex-col items-center gap-3">
        {SECTION_LABELS.map((label, index) => (
          <button
            key={label}
            onClick={() => scrollToSection(index)}
            className="group relative flex items-center"
            aria-label={`跳转到${label}`}
          >
            <span className={`
              absolute right-8 px-2 py-1 rounded text-xs font-medium whitespace-nowrap
              bg-gray-800 text-white opacity-0 group-hover:opacity-100
              transition-opacity pointer-events-none
            `}>
              {label}
            </span>
            <motion.div
              className={`rounded-full transition-colors ${
                currentSection === index
                  ? 'bg-[#4C9755] w-3 h-3'
                  : 'bg-gray-300 hover:bg-[#A9D098] w-2.5 h-2.5'
              }`}
              animate={currentSection === index ? { scale: [1, 1.3, 1] } : {}}
              transition={{ duration: 0.4 }}
            />
          </button>
        ))}
      </nav>

      {/* Sections slider */}
      <motion.div
        style={{ height: viewH * totalSections }}
        animate={{ y: -(currentSection * viewH) }}
        transition={{ duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
      >

      {/* Hero Section - Full screen blurred background */}
      <section className="relative flex items-center justify-center overflow-hidden" style={{ height: viewH }}>
        {/* Blurred background image */}
        <div className="absolute inset-0">
          <img
            src="/faulttree.png"
            alt=""
            className="w-full h-full object-cover scale-110 blur-[12px] brightness-105"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-white/70 via-[#A9D098]/30 to-white/80" />
        </div>

        {/* Centered content */}
        <div className="relative z-10 text-center px-6 max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-6"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#4C9755]/10 backdrop-blur-sm text-[#4C9755] rounded-full text-sm font-medium border border-[#4C9755]/20">
              <Sparkles className="h-4 w-4" />
              专业故障树分析平台
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold text-gray-800 leading-tight mb-6"
          >
            精准高效构建
            <span className="block bg-gradient-to-r from-[#A9D098] via-[#7AB87E] to-[#4C9755] bg-clip-text text-transparent mt-2">
              专业故障树
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-lg md:text-xl text-gray-600 leading-relaxed mb-10 max-w-2xl mx-auto"
          >
            专为安全工程师、可靠性专家和风险分析师设计的专业故障树分析工具。
            通过直观的可视化界面创建、分析和导出故障树。
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link to="/flow">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button size="lg" className="gap-2 text-base h-14 px-10 shadow-2xl shadow-[#4C9755]/40 bg-gradient-to-r from-[#A9D098] to-[#4C9755] hover:from-[#8AB880] hover:to-[#3A7341] font-semibold">
                  启动编辑器
                  <ArrowRight className="h-5 w-5" />
                </Button>
              </motion.div>
            </Link>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-6 h-10 border-2 border-[#4C9755]/30 rounded-full flex justify-center pt-2">
            <div className="w-1.5 h-3 bg-[#4C9755]/50 rounded-full" />
          </div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="flex flex-col justify-center overflow-hidden" style={{ height: viewH }}>
        <div className="max-w-7xl mx-auto px-6 w-full">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <h2 className="text-4xl font-bold mb-3">项目数据</h2>
            <p className="text-xl text-gray-600">用数字说话</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="grid grid-cols-2 lg:grid-cols-4 gap-8"
          >
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <Card className="p-8 text-center border-2 hover:border-[#A9D098] transition-all hover:shadow-lg">
                  <stat.icon className="h-10 w-10 mx-auto mb-4 text-[#4C9755]" />
                  <div className="text-4xl font-bold bg-gradient-to-r from-[#A9D098] to-[#4C9755] bg-clip-text text-transparent">
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-600 mt-2">{stat.label}</div>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="flex flex-col justify-center overflow-hidden" style={{ height: viewH }}>
        <div className="max-w-7xl mx-auto px-6 w-full">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-10"
          >
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{ type: "spring", stiffness: 200 }}
              className="inline-block mb-4"
            >
              <div className="w-12 h-12 bg-gradient-to-r from-[#A9D098] to-[#4C9755] rounded-xl flex items-center justify-center mx-auto">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
            </motion.div>
            <h2 className="text-4xl font-bold mb-3">强大功能</h2>
            <p className="text-xl text-gray-600">全面的故障树分析所需的一切</p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <Card className="p-5 h-full hover:shadow-2xl transition-all border-2 hover:border-transparent relative overflow-hidden group">
                  <div
                    className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity`}
                  />
                  <div
                    className={`w-12 h-12 bg-gradient-to-br ${feature.gradient} rounded-xl flex items-center justify-center mb-3 relative`}
                  >
                    <feature.icon className="h-6 w-6 text-white relative z-10" />
                  </div>
                  <h3 className="font-bold text-lg mb-2 relative z-10">{feature.title}</h3>
                  <p className="text-gray-600 relative z-10 leading-relaxed text-sm">{feature.description}</p>
                  <div className={`absolute top-0 right-0 w-16 h-16 bg-gradient-to-br ${feature.gradient} opacity-5 rounded-bl-full`} />
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="flex items-center bg-gradient-to-b from-[#A9D098]/10 via-[#4C9755]/10 to-white py-20 relative overflow-hidden" style={{ height: viewH }}>
        {/* Decorative background pattern */}
        <div className="absolute inset-0 opacity-5">
          <img
            src="/image.png"
            alt=""
            className="w-full h-full object-cover"
          />
        </div>

        <div className="max-w-7xl mx-auto px-6 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              className="order-2 lg:order-1"
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <motion.div
                whileHover={{ scale: 1.03 }}
                transition={{ type: "spring", stiffness: 300 }}
                className="relative"
              >
                <div className="absolute -inset-4 bg-gradient-to-r from-[#A9D098]/20 to-[#4C9755]/20 rounded-3xl blur-2xl" />
                <img
                  src="/image.png"
                  alt="Network Diagram"
                  className="rounded-2xl shadow-2xl w-full h-auto relative ring-1 ring-gray-200/50"
                />
              </motion.div>
            </motion.div>

            <motion.div
              className="space-y-6 order-1 lg:order-2"
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="inline-block px-4 py-2 bg-gradient-to-r from-[#A9D098]/30 to-[#4C9755]/30 text-[#4C9755] rounded-full text-sm font-medium">
                行业应用
              </div>
              <h2 className="text-4xl font-bold">设备故障分析</h2>
              <p className="text-lg text-gray-600">
                EET 故障树分析工具能够深入分析设备故障根因，
                支持多类型设备的综合诊断和快速排查。
              </p>
              <ul className="space-y-4">
                {[
                  { name: '电力系统故障', icon: '🔌' },
                  { name: '机械传动故障', icon: '⚙️' },
                  { name: '液压系统故障', icon: '💧' },
                  { name: '气动系统故障', icon: '💨' },
                  { name: '电气控制故障', icon: '🔧' },
                  { name: '通讯设备故障', icon: '📡' },
                ].map((industry, index) => (
                  <motion.li
                    key={industry.name}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ x: 10 }}
                    className="flex items-center gap-3 group"
                  >
                    <motion.div
                      whileHover={{ scale: 1.2, rotate: 360 }}
                      transition={{ type: "spring", stiffness: 300 }}
                      className="w-10 h-10 bg-gradient-to-br from-green-400 to-emerald-500 rounded-lg flex items-center justify-center text-white shadow-lg"
                    >
                      <span>{industry.icon}</span>
                    </motion.div>
                    <span className="text-lg font-medium group-hover:text-[#4C9755] transition-colors">
                      {industry.name}
                    </span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Core Docs Section */}
      <section className="flex items-center bg-gradient-to-b from-white via-[#4C9755]/5 to-white overflow-hidden" style={{ height: viewH }}>
        <div className="max-w-5xl mx-auto px-6 w-full">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{ type: "spring", stiffness: 200 }}
              className="inline-block mb-4"
            >
              <div className="w-12 h-12 bg-gradient-to-r from-[#A9D098] to-[#4C9755] rounded-xl flex items-center justify-center mx-auto">
                <BookOpen className="h-6 w-6 text-white" />
              </div>
            </motion.div>
            <h2 className="text-4xl font-bold mb-4">核心技术文档</h2>
            <p className="text-xl text-gray-600">深入了解系统背后的关键算法与架构设计</p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-8 items-stretch">
            {/* 知识图谱文档卡片 */}
            <Link to="/docs/knowledge-graph" className="no-underline h-full block">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
                whileHover={{ y: -8 }}
                className="h-full"
              >
                <Card className="p-8 h-full border-2 hover:border-[#4C9755] hover:shadow-2xl transition-all relative overflow-hidden group cursor-pointer">
                  <div className="absolute inset-0 bg-gradient-to-br from-[#A9D098]/10 to-[#4C9755]/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-[#A9D098] to-[#4C9755] opacity-5 rounded-bl-full" />

                  <div className="relative z-10">
                    <div className="w-14 h-14 bg-gradient-to-br from-[#A9D098] to-[#4C9755] rounded-xl flex items-center justify-center mb-5">
                      <Network className="h-7 w-7 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold mb-3 group-hover:text-[#4C9755] transition-colors">
                      知识图谱模块
                    </h3>
                    <p className="text-gray-600 leading-relaxed mb-4">
                      基于 LightRAG 与 HippoRAG 的轻量化知识图谱方案，采用 Schema 定向抽取与 NetworkX 内存图，实现向量寻点 + BFS 多跳推理的两阶段检索策略，在资源受限环境下高效运行。
                    </p>
                    <div className="flex items-center gap-2 text-[#4C9755] font-medium text-sm">
                      <span>阅读文档</span>
                      <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </Card>
              </motion.div>
            </Link>

            {/* 上下文管理文档卡片 */}
            <Link to="/docs/context-management" className="no-underline h-full block">
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
                className="h-full"
                whileHover={{ y: -8 }}
              >
                <Card className="p-8 h-full border-2 hover:border-[#4C9755] hover:shadow-2xl transition-all relative overflow-hidden group cursor-pointer">
                  <div className="absolute inset-0 bg-gradient-to-br from-[#A9D098]/10 to-[#4C9755]/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-[#A9D098] to-[#4C9755] opacity-5 rounded-bl-full" />

                  <div className="relative z-10">
                    <div className="w-14 h-14 bg-gradient-to-br from-[#A9D098] to-[#4C9755] rounded-xl flex items-center justify-center mb-5">
                      <Brain className="h-7 w-7 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold mb-3 group-hover:text-[#4C9755] transition-colors">
                      上下文管理算法
                    </h3>
                    <p className="text-gray-600 leading-relaxed mb-4">
                      融合 MMR 去重、Retrieval Head 重排、PathRAG 路径剪枝、Token 分级预算与 MemAgent 历史分层等多篇论文核心思想，实现检索后上下文的智能编排与压缩。
                    </p>
                    <div className="flex items-center gap-2 text-[#4C9755] font-medium text-sm">
                      <span>阅读文档</span>
                      <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </Card>
              </motion.div>
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="flex items-center overflow-hidden" style={{ height: viewH }}><div className="max-w-7xl mx-auto px-6 py-20 w-full">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">开发人员</h2>
          <p className="text-xl text-gray-600">主要开发人员名单</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              name: '唐宏健',
              role: '全栈工程师 - 架构师',
              company: '',
              content: '负责系统结构设计，核心功能开发和整体项目管理，设计了完备的promote算法与轻量化知识图谱构建方案，确保系统的高性能和可扩展性。',
              avatar: '👨‍💻',   
            },
            {
              name: '周博文',
              role: '后端工程师',
              company: '',
              content: '负责统筹进度和后端辅助开发，定期对系统进行测试，确保系统的高性能和可靠性。',
              avatar: '👩‍💼',
            },
            {
              name: '刘益铭',
              role: '前端工程师',
              company: '',
              content: '负责前端开发，使用React和Tailwind CSS构建了这个响应式界面，进行了大量的动画和交互设计，提升用户体验。',
              avatar: '👨‍💻',
            },
          ].map((testimonial, index) => (
            <motion.div
              key={testimonial.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.2 }}
              whileHover={{ y: -5 }}
            >
              <Card className="p-6 h-full border-2 hover:border-[#A9D098] hover:shadow-xl transition-all">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-[#A9D098] to-[#4C9755] rounded-full flex items-center justify-center text-2xl">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-semibold">{testimonial.name}</div>
                    <div className="text-sm text-gray-500">{testimonial.role}</div>
                  </div>
                </div>
                <p className="text-gray-600 italic mb-4">"{testimonial.content}"</p>
                <div className="text-sm text-[#4C9755] font-medium">{testimonial.company}</div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div></section>

      {/* CTA + Footer Section */}
      <section className="flex flex-col justify-center border-t bg-gradient-to-b from-white to-[#A9D098]/10 py-12 overflow-hidden" style={{ height: viewH }}>
        <div className="max-w-7xl mx-auto px-6 w-full mb-16">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative"
        >
          <div className="bg-gradient-to-r from-[#A9D098] via-[#7AB87E] to-[#4C9755] rounded-3xl p-12 text-center text-white relative overflow-hidden shadow-2xl">
            {/* Animated background elements */}
            <motion.div
              className="absolute top-0 left-0 w-64 h-64 bg-white/10 rounded-full blur-3xl"
              animate={{ x: [0, 100, 0], y: [0, 50, 0] }}
              transition={{ duration: 10, repeat: Infinity }}
            />
            <motion.div
              className="absolute bottom-0 right-0 w-80 h-80 bg-white/10 rounded-full blur-3xl"
              animate={{ x: [0, -100, 0], y: [0, -50, 0] }}
              transition={{ duration: 12, repeat: Infinity }}
            />

            <div className="absolute inset-0 opacity-10">
              <img
                src="/faulttree.png"
                alt=""
                className="w-full h-full object-cover"
              />
            </div>

            <div className="relative z-10">
              <motion.div
                initial={{ scale: 0 }}
                whileInView={{ scale: 1 }}
                viewport={{ once: true }}
                transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
                className="inline-block mb-6"
              >
                <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto">
                  <Sparkles className="h-8 w-8" />
                </div>
              </motion.div>

              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 }}
                className="text-4xl font-bold mb-4"
              >
                准备好构建您的故障树了吗？
              </motion.h2>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.4 }}
                className="text-xl mb-8 opacity-90"
              >
                使用我们强大的可视化编辑器，开始分析系统可靠性和安全性。
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 }}
              >
                <Link to="/flow">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Button size="lg" variant="secondary" className="gap-2 text-base h-14 px-10 shadow-2xl font-semibold">
                      立即启动编辑器
                      <ArrowRight className="h-5 w-5" />
                    </Button>
                  </motion.div>
                </Link>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>

        {/* Footer content */}
        <div className="max-w-7xl mx-auto px-6 w-full">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <GitBranch className="h-5 w-5 text-[#4C9755]" />
                <span className="font-bold bg-gradient-to-r from-[#A9D098] to-[#4C9755] bg-clip-text text-transparent">
                  EET Fault Tree
                </span>
              </div>
              <p className="text-sm text-gray-600">
                专业的故障树分析工具，
                为可靠性工程师而生。
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">产品</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">功能特性</span></li>
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">定价方案</span></li>
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">案例研究</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">资源</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><Link to="/docs/knowledge-graph" className="hover:text-[#4C9755] transition-colors cursor-pointer">知识图谱文档</Link></li>
                <li><Link to="/docs/context-management" className="hover:text-[#4C9755] transition-colors cursor-pointer">上下文管理算法</Link></li>
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">教程视频</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">公司</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">关于我们</span></li>
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">联系方式</span></li>
                <li><span className="hover:text-[#4C9755] transition-colors cursor-pointer">加入我们</span></li>
              </ul>
            </div>
          </div>
          <div className="border-t pt-8 text-center text-gray-600">
            <p>© 2026 EET Fault Tree. Built with 青色交流电灯</p>
          </div>
        </div>
      </section>
      </motion.div>
    </div>
  );
}
