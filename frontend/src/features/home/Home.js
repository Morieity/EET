import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Network, Shield, Zap, GitBranch, TrendingUp, Users, Award, Sparkles, Code, FileJson } from 'lucide-react';
import { Button } from '../../ui/button';
import { Card } from '../../ui/card';
import { motion } from 'motion/react';

export default function Home() {

  const stats = [
    { label: '代码行数', value: '38352', icon: Users },
    { label: '论文篇数', value: '50,000+', icon: GitBranch },
    { label: '分析准确率', value: '99.9%', icon: Award },
    { label: '响应时间', value: '30-60s', icon: TrendingUp },
  ];

  const features = [
    {
      icon: Network,
      title: '可视化编辑器',
      description: '直观的拖放界面，轻松构建复杂故障树。添加门、事件和连接，一切尽在掌握。',
      color: 'blue',
      gradient: 'from-blue-500 to-cyan-500',
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
      color: 'purple',
      gradient: 'from-purple-500 to-pink-500',
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
      color: 'indigo',
      gradient: 'from-indigo-500 to-purple-500',
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
    <div className="min-h-screen bg-slate-50 overflow-hidden">
      {/* Hero Section - Full screen blurred background */}
      <section className="relative h-screen flex items-center justify-center overflow-hidden">
        {/* Blurred background image */}
        <div className="absolute inset-0">
          <img
            src="/faulttree.png"
            alt=""
            className="w-full h-full object-cover scale-110 blur-sm"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-slate-900/60 via-slate-900/50 to-slate-900/70" />
        </div>

        {/* Centered content */}
        <div className="relative z-10 text-center px-6 max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-6"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/15 backdrop-blur-sm text-white/90 rounded-full text-sm font-medium border border-white/20">
              <Sparkles className="h-4 w-4" />
              专业故障树分析平台
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-tight mb-6"
          >
            精准高效构建
            <span className="block bg-gradient-to-r from-blue-400 via-cyan-300 to-purple-400 bg-clip-text text-transparent mt-2">
              专业故障树
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-lg md:text-xl text-white/80 leading-relaxed mb-10 max-w-2xl mx-auto"
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
                <Button size="lg" className="gap-2 text-base h-14 px-10 shadow-2xl shadow-blue-500/40 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 font-semibold">
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
          <div className="w-6 h-10 border-2 border-white/30 rounded-full flex justify-center pt-2">
            <div className="w-1.5 h-3 bg-white/50 rounded-full" />
          </div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="max-w-7xl mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="grid grid-cols-2 lg:grid-cols-4 gap-6"
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
              <Card className="p-6 text-center border-2 hover:border-blue-300 transition-all hover:shadow-lg">
                <stat.icon className="h-8 w-8 mx-auto mb-3 text-blue-600" />
                <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-600 mt-1">{stat.label}</div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ type: "spring", stiffness: 200 }}
            className="inline-block mb-4"
          >
            <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center mx-auto">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
          </motion.div>
          <h2 className="text-4xl font-bold mb-4">强大功能</h2>
          <p className="text-xl text-gray-600">全面的故障树分析所需的一切</p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ y: -8 }}

            >
              <Card className="p-6 h-full hover:shadow-2xl transition-all border-2 hover:border-transparent relative overflow-hidden group">
                {/* Animated gradient background on hover */}
                <div
                  className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity`}
                />

                <div
                  className={`w-14 h-14 bg-gradient-to-br ${feature.gradient} rounded-xl flex items-center justify-center mb-4 relative`}
                >
                  <feature.icon className="h-7 w-7 text-white relative z-10" />
                </div>

                <h3 className="font-bold text-xl mb-3 relative z-10">{feature.title}</h3>
                <p className="text-gray-600 relative z-10 leading-relaxed">{feature.description}</p>

                {/* Corner decoration */}
                <div className={`absolute top-0 right-0 w-20 h-20 bg-gradient-to-br ${feature.gradient} opacity-5 rounded-bl-full`} />
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="bg-gradient-to-b from-blue-50/50 via-purple-50/50 to-white py-20 relative">
        {/* Decorative background pattern */}
        <div className="absolute inset-0 opacity-5">
          <img
            src="/faulttree.png"
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
                <div className="absolute -inset-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-3xl blur-2xl" />
                <img
                  src="/faulttree.png"
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
              <div className="inline-block px-4 py-2 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 rounded-full text-sm font-medium">
                行业应用
              </div>
              <h2 className="text-4xl font-bold">适用于多个行业</h2>
              <p className="text-lg text-gray-600">
                EET Fault Tree 深受各行业专业人士信赖，
                用于关键的安全性和可靠性分析。
              </p>
              <ul className="space-y-4">
                {[
                  { name: '航空航天', icon: '✈️' },
                  { name: '核电系统', icon: '⚡' },
                  { name: '汽车制造', icon: '🚗' },
                  { name: '化工处理', icon: '⚗️' },
                  { name: '医疗设备', icon: '🏥' },
                  { name: '软件系统', icon: '💻' },
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
                    <span className="text-lg font-medium group-hover:text-blue-600 transition-colors">
                      {industry.name}
                    </span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="max-w-7xl mx-auto px-6 py-20">
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
              role: '全栈工程师',
              company: '中国航空集团',
              content: '这个工具大大提高了我们的故障树分析效率，界面直观，功能强大。',
              avatar: '👨‍💻',   
            },
            {
              name: '周博文',
              role: '后端工程师',
              company: '华为技术有限公司',
              content: '导出功能非常实用，可以轻松与团队分享分析结果，协作更加顺畅。',
              avatar: '👩‍💼',
            },
            {
              name: '刘益铭',
              role: '前端工程师',
              company: '中国石化',
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
              <Card className="p-6 h-full border-2 hover:border-blue-300 hover:shadow-xl transition-all">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-2xl">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-semibold">{testimonial.name}</div>
                    <div className="text-sm text-gray-500">{testimonial.role}</div>
                  </div>
                </div>
                <p className="text-gray-600 italic mb-4">"{testimonial.content}"</p>
                <div className="text-sm text-blue-600 font-medium">{testimonial.company}</div>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative"
        >
          <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 rounded-3xl p-12 text-center text-white relative overflow-hidden shadow-2xl">
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
      </section>

      {/* Footer */}
      <footer className="border-t bg-gradient-to-b from-slate-50 to-slate-100 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <GitBranch className="h-5 w-5 text-blue-600" />
                <span className="font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
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
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">功能特性</span></li>
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">定价方案</span></li>
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">案例研究</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">资源</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">文档中心</span></li>
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">教程视频</span></li>
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">API 文档</span></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">公司</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">关于我们</span></li>
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">联系方式</span></li>
                <li><span className="hover:text-blue-600 transition-colors cursor-pointer">加入我们</span></li>
              </ul>
            </div>
          </div>
          <div className="border-t pt-8 text-center text-gray-600">
            <p>© 2026 EET Fault Tree. Built with React Flow & DeepSeek AI</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
