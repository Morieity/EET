import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, ChevronRight, Menu, X, BookOpen, GitBranch } from 'lucide-react';

const DOC_NAV = [
  { title: '知识图谱模块', path: '/docs/knowledge-graph' },
  { title: '上下文管理算法', path: '/docs/context-management' },
];

export default function DocLayout({ title, subtitle, sections, children }) {
  const [activeSection, setActiveSection] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const contentRef = useRef(null);
  const location = useLocation();

  const handleScroll = useCallback(() => {
    if (!contentRef.current) return;
    const container = contentRef.current;
    const scrollTop = container.scrollTop;

    for (let i = sections.length - 1; i >= 0; i--) {
      const el = document.getElementById(sections[i].id);
      if (el && el.offsetTop - container.offsetTop <= scrollTop + 120) {
        setActiveSection(sections[i].id);
        return;
      }
    }
    if (sections.length > 0) setActiveSection(sections[0].id);
  }, [sections]);

  useEffect(() => {
    const container = contentRef.current;
    if (!container) return;
    container.addEventListener('scroll', handleScroll);
    handleScroll();
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el && contentRef.current) {
      const container = contentRef.current;
      const top = el.offsetTop - container.offsetTop - 80;
      container.scrollTo({ top, behavior: 'smooth' });
    }
    setMobileMenuOpen(false);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Top Nav */}
      <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 lg:px-6 shrink-0 z-30">
        <Link to="/" className="flex items-center gap-2 text-gray-600 hover:text-[#4C9755] transition-colors mr-6">
          <ArrowLeft className="h-4 w-4" />
          <GitBranch className="h-4 w-4 text-[#4C9755]" />
          <span className="font-semibold text-sm bg-gradient-to-r from-[#4C9755] to-[#A9D098] bg-clip-text text-transparent">EET</span>
        </Link>

        <div className="hidden md:flex items-center gap-1 text-sm text-gray-500">
          <BookOpen className="h-4 w-4" />
          <span>文档</span>
          <ChevronRight className="h-3 w-3" />
          <span className="text-gray-800 font-medium">{title}</span>
        </div>

        <nav className="hidden md:flex items-center gap-4 ml-auto">
          {DOC_NAV.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`text-sm px-3 py-1.5 rounded-md transition-colors ${
                location.pathname === item.path
                  ? 'bg-[#4C9755]/10 text-[#4C9755] font-medium'
                  : 'text-gray-600 hover:text-[#4C9755] hover:bg-gray-100'
              }`}
            >
              {item.title}
            </Link>
          ))}
        </nav>

        <button
          className="md:hidden ml-auto p-2 text-gray-600"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden relative">
        {/* Mobile menu overlay */}
        {mobileMenuOpen && (
          <div className="absolute inset-0 z-40 md:hidden">
            <div className="absolute inset-0 bg-black/30" onClick={() => setMobileMenuOpen(false)} />
            <div className="absolute left-0 top-0 bottom-0 w-72 bg-white shadow-xl overflow-y-auto p-4">
              <div className="mb-4 pb-3 border-b">
                {DOC_NAV.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`block text-sm px-3 py-2 rounded-md mb-1 ${
                      location.pathname === item.path
                        ? 'bg-[#4C9755]/10 text-[#4C9755] font-medium'
                        : 'text-gray-600'
                    }`}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {item.title}
                  </Link>
                ))}
              </div>
              <SidebarContent
                sections={sections}
                activeSection={activeSection}
                onNavigate={scrollTo}
              />
            </div>
          </div>
        )}

        {/* Desktop Sidebar */}
        <aside className="hidden md:block w-64 lg:w-72 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
          <div className="p-5">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">目录</h3>
            <SidebarContent
              sections={sections}
              activeSection={activeSection}
              onNavigate={scrollTo}
            />
          </div>
        </aside>

        {/* Main Content */}
        <main ref={contentRef} className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 lg:px-12 py-10">
            {/* Page header */}
            <div className="mb-10 pb-8 border-b border-gray-200">
              <h1 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-3">{title}</h1>
              {subtitle && <p className="text-lg text-gray-500">{subtitle}</p>}
            </div>
            {/* Document content */}
            <div className="doc-content">{children}</div>
          </div>
        </main>
      </div>
    </div>
  );
}

function SidebarContent({ sections, activeSection, onNavigate }) {
  return (
    <nav className="space-y-0.5">
      {sections.map((section) => (
        <button
          key={section.id}
          onClick={() => onNavigate(section.id)}
          className={`w-full text-left text-sm py-1.5 pr-2 rounded-md transition-all ${
            section.level === 2 ? 'pl-3' : 'pl-6'
          } ${
            activeSection === section.id
              ? 'text-[#4C9755] font-medium bg-[#4C9755]/8'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          }`}
        >
          {activeSection === section.id && (
            <span className="inline-block w-0.5 h-4 bg-[#4C9755] rounded-full mr-2 align-middle" />
          )}
          {section.title}
        </button>
      ))}
    </nav>
  );
}

/* Reusable doc components */
export function DocSection({ id, title, children }) {
  return (
    <section id={id} className="mb-12 scroll-mt-24">
      <h2 className="text-2xl font-bold text-gray-900 mb-4 pb-2 border-b border-gray-100">{title}</h2>
      {children}
    </section>
  );
}

export function DocSubSection({ id, title, children }) {
  return (
    <div id={id} className="mb-8 scroll-mt-24">
      <h3 className="text-xl font-semibold text-gray-800 mb-3">{title}</h3>
      {children}
    </div>
  );
}

export function DocParagraph({ children }) {
  return <p className="text-gray-700 leading-relaxed mb-4">{children}</p>;
}

export function DocTable({ headers, rows }) {
  return (
    <div className="overflow-x-auto mb-6 rounded-lg border border-gray-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#4C9755]/10">
            {headers.map((h, i) => (
              <th key={i} className="text-left px-4 py-3 font-semibold text-[#4C9755] border-b border-gray-200">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 text-gray-700 border-b border-gray-100">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DocCode({ children, title }) {
  return (
    <div className="mb-6 rounded-lg overflow-hidden border border-gray-800">
      {title && (
        <div className="bg-gray-800 px-4 py-2 text-xs text-gray-400 border-b border-gray-700">
          {title}
        </div>
      )}
      <pre className="bg-gray-900 text-gray-100 p-4 overflow-x-auto text-sm leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  );
}

export function DocList({ items, ordered }) {
  const Tag = ordered ? 'ol' : 'ul';
  return (
    <Tag className={`mb-4 space-y-2 text-gray-700 ${ordered ? 'list-decimal' : 'list-disc'} pl-6`}>
      {items.map((item, i) => (
        <li key={i} className="leading-relaxed">{item}</li>
      ))}
    </Tag>
  );
}

export function DocCallout({ children, type = 'info' }) {
  const styles = {
    info: 'bg-[#4C9755]/5 border-[#4C9755]/30 text-[#3A7341]',
    tip: 'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
  };
  return (
    <div className={`mb-6 p-4 rounded-lg border-l-4 ${styles[type]}`}>
      {children}
    </div>
  );
}

export function DocFlowChart({ children }) {
  return (
    <div className="mb-6 bg-gray-900 rounded-lg p-5 overflow-x-auto">
      <pre className="text-green-400 text-sm leading-relaxed font-mono">{children}</pre>
    </div>
  );
}
