import React, { useState, useRef, useEffect } from 'react';
import {
  LayoutDashboard,
  CheckSquare,
  Users,
  BarChart2,
  BookOpen,
  AlertCircle,
  Wrench,
  Sun,
  Moon,
  Search,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Menu,
  X,
  FileText,
  Shield,
  ExternalLink
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar } from '../primitives/Avatar';
import { Button } from '../primitives/Button';
import { Kbd } from '../primitives/Kbd';
import { ToastContainer } from '../primitives/Toast';
import { CommandPalette } from '../primitives/CommandPalette';
import { EvidenceDrawer } from '../primitives/EvidenceDrawer';
import type { RoleType } from '../../types';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { currentPath, navigate, theme, toggleTheme, role, setRole, setCommandPaletteOpen, cases } = useApp();
  const firstCasePath = cases.length > 0 ? `/cases/${cases[0].id}` : '/';

  // Role popover state
  const [isRoleOpen, setIsRoleOpen] = useState(false);
  const roleRef = useRef<HTMLDivElement>(null);

  // Sidebar collapsed state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('vendorgate:sidebar-collapsed') === 'true';
  });

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('vendorgate:sidebar-collapsed', String(next));
      return next;
    });
  };

  // Mobile drawer state
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (roleRef.current && !roleRef.current.contains(e.target as Node)) {
        setIsRoleOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const roles: RoleType[] = ['Requester', 'AP Analyst', 'Controller', 'Compliance', 'Auditor', 'Admin'];

  // Work routes that display the sidebar on desktop
  const isWorkRoute =
    currentPath.startsWith('/cases') ||
    currentPath.startsWith('/approvals') ||
    currentPath.startsWith('/vendors');

  const navLinks = [
    { label: 'Dashboard', path: '/' },
    { label: 'Submit', path: '/submit' },
    { label: 'Cases', get path() { return firstCasePath; } },
    { label: 'Approvals', path: '/approvals' },
    { label: 'Vendors', path: '/vendors' },
    { label: 'Benchmark', path: '/benchmark' },
    { label: 'Policy', path: '/policy' },
    { label: 'Fool-it', path: '/foolit' },
  ];

  const sidebarSections = [
    {
      title: 'Work',
      items: [
        { label: 'Approvals', path: '/approvals', icon: <CheckSquare size={16} /> },
        { label: 'Cases', get path() { return firstCasePath; }, icon: <FileText size={16} /> },
        { label: 'Vendors', path: '/vendors', icon: <Users size={16} /> },
      ]
    },
    {
      title: 'Analysis',
      items: [
        { label: 'Benchmark', path: '/benchmark', icon: <BarChart2 size={16} /> },
        { label: 'Policy', path: '/policy', icon: <BookOpen size={16} /> },
        { label: 'Fool-it Lab', path: '/foolit', icon: <AlertCircle size={16} /> },
      ]
    },
    {
      title: 'Admin',
      items: [
        { label: 'Control Room', path: '/admin', icon: <Wrench size={16} /> },
      ]
    }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-primary selection:bg-accent-subtle selection:text-accent-fg">
      {/* Skip to main content link for a11y */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* TOP BAR — 56px height — sticky */}
      <header className="h-14 sticky top-0 z-40 border-b border-border-subtle bg-surface/80 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 md:px-8">
        {/* Left: Logo & Nav */}
        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2.5 focus-ring rounded-[4px] cursor-pointer"
          >
            {/* Geometric SVG glyph: Two overlapping angled precision shapes */}
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-accent shrink-0"
              aria-label="VendorGate Logo"
            >
              <path
                d="M3 4L12 20L21 4H16L12 12.5L8 4H3Z"
                fill="currentColor"
              />
              <path
                d="M8 4L12 11.5L16 4H12L8 4Z"
                fill="currentColor"
                fillOpacity="0.4"
              />
            </svg>
            <span className="text-[14px] font-semibold text-text-primary tracking-[-0.01em]">
              VendorGate
            </span>
          </button>

          {/* Desktop Horizontal Nav */}
          <nav aria-label="Main Navigation" className="hidden lg:flex items-center gap-1">
            {navLinks.map(link => {
              const isActive =
                link.path === '/'
                  ? currentPath === '/'
                  : currentPath.startsWith(link.path);

              return (
                <button
                  key={link.path}
                  type="button"
                  onClick={() => navigate(link.path)}
                  className={`relative h-14 px-3 flex items-center text-[13px] font-medium transition-colors cursor-pointer select-none ${
                    isActive
                      ? 'text-text-primary'
                      : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  <span>{link.label}</span>
                  {isActive && (
                    <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-accent transition-all duration-180 ease-[cubic-bezier(0.16,1,0.3,1)]" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Right: Search, Theme Toggle, Role Switcher */}
        <div className="flex items-center gap-3">
          {/* Search Button (320px wide on desktop) */}
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            className="hidden sm:flex items-center justify-between w-48 md:w-72 lg:w-80 h-8 px-3 rounded-[6px] border border-border bg-subtle/50 text-text-tertiary text-[13px] hover:border-border-strong transition-colors focus-ring cursor-pointer"
          >
            <div className="flex items-center gap-2 truncate">
              <Search size={14} className="shrink-0" />
              <span className="truncate">Search anything…</span>
            </div>
            <Kbd>⌘K</Kbd>
          </button>

          {/* Theme Toggle (32px ghost button) */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            className="w-8 h-8 flex items-center justify-center rounded-[6px] text-text-secondary hover:text-text-primary hover:bg-subtle transition-colors focus-ring cursor-pointer"
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
          </button>

          {/* Role Switcher Pill */}
          <div className="relative" ref={roleRef}>
            <button
              type="button"
              onClick={() => setIsRoleOpen(!isRoleOpen)}
              aria-haspopup="true"
              aria-expanded={isRoleOpen}
              className="flex items-center gap-2 h-8 px-2.5 rounded-full border border-border bg-surface hover:bg-subtle text-text-primary text-[13px] font-medium transition-colors focus-ring cursor-pointer select-none"
            >
              <Avatar name={role} size={24} />
              <span className="hidden sm:inline">{role}</span>
              <ChevronDown size={14} className="text-text-tertiary" />
            </button>

            {/* Role Switcher Popover */}
            {isRoleOpen && (
              <div className="absolute right-0 top-[calc(100%+6px)] w-56 rounded-[12px] border border-border bg-surface shadow-md dark:shadow-none p-1.5 z-50 animate-in zoom-in-95 duration-120">
                <div className="px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary border-b border-border-subtle mb-1">
                  Active Security Role
                </div>
                {roles.map(r => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => {
                      setRole(r);
                      setIsRoleOpen(false);
                    }}
                    className={`w-full h-8 px-3 flex items-center justify-between rounded-[6px] text-[13px] text-left transition-colors cursor-pointer select-none ${
                      role === r
                        ? 'bg-accent-subtle text-accent-fg font-medium border-l-2 border-accent'
                        : 'text-text-secondary hover:text-text-primary hover:bg-subtle'
                    }`}
                  >
                    <span>{r}</span>
                    {role === r && <span className="text-[11px] font-mono">Active</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* BODY SHELL: Optional Sidebar + Main Content */}
      <div className="flex-1 flex">
        {/* SIDEBAR (only on work routes: /cases, /approvals, /vendors) */}
        {isWorkRoute && (
          <aside
            aria-label="Work Sidebar"
            className={`hidden md:flex flex-col border-r border-border-subtle bg-muted transition-all duration-240 shrink-0 ${
              isSidebarCollapsed ? 'w-14' : 'w-60'
            }`}
          >
            <div className="p-3 space-y-6 flex-1 overflow-y-auto">
              {sidebarSections.map(section => (
                <div key={section.title} className="space-y-1">
                  {!isSidebarCollapsed && (
                    <div className="px-2.5 text-[11px] font-medium uppercase tracking-[0.04em] text-text-tertiary mb-1">
                      {section.title}
                    </div>
                  )}
                  {section.items.map(item => {
                    const isActive = currentPath.startsWith(item.path);
                    return (
                      <button
                        key={item.label}
                        type="button"
                        onClick={() => navigate(item.path)}
                        title={isSidebarCollapsed ? item.label : undefined}
                        className={`w-full h-9 flex items-center gap-2.5 px-2.5 rounded-[6px] text-[13px] transition-colors cursor-pointer select-none ${
                          isActive
                            ? 'bg-surface text-text-primary font-medium border-l-2 border-accent shadow-xs dark:shadow-none'
                            : 'text-text-secondary hover:text-text-primary hover:bg-subtle'
                        } ${isSidebarCollapsed ? 'justify-center' : ''}`}
                      >
                        <span className={isActive ? 'text-accent' : 'text-text-tertiary'}>
                          {item.icon}
                        </span>
                        {!isSidebarCollapsed && <span>{item.label}</span>}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Collapse toggle button at bottom */}
            <div className="p-2 border-t border-border-subtle flex justify-end">
              <button
                type="button"
                onClick={toggleSidebar}
                aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                className="w-full h-8 flex items-center justify-center rounded-[6px] text-text-tertiary hover:text-text-primary hover:bg-subtle transition-colors cursor-pointer"
              >
                {isSidebarCollapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
              </button>
            </div>
          </aside>
        )}

        {/* MAIN CONTENT AREA */}
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 w-full max-w-[1280px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8 focus:outline-none flex flex-col justify-between"
        >
          <div className="flex-1">
            {children}
          </div>

          {/* Persistent Footer */}
          <footer className="mt-16 pt-6 border-t border-border-subtle flex flex-col sm:flex-row items-center justify-between gap-3 text-[12px] text-text-tertiary">
            <div>
              <span>VendorGate v0.6.0 · policy </span>
              <span className="font-mono text-text-secondary">a4f89c12</span>
            </div>
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => navigate('/policy')}
                className="hover:text-text-primary transition-colors cursor-pointer"
              >
                Policy Specs
              </button>
              <span>·</span>
              <button
                type="button"
                onClick={() => navigate('/benchmark')}
                className="hover:text-text-primary transition-colors cursor-pointer"
              >
                Benchmark Report
              </button>
            </div>
          </footer>
        </main>
      </div>

      {/* MOBILE BOTTOM NAV BAR (<768px) */}
      <nav aria-label="Mobile Bottom Nav" className="md:hidden fixed bottom-0 left-0 right-0 h-14 bg-surface border-t border-border-subtle z-40 flex items-center justify-around px-2">
        <button
          type="button"
          onClick={() => navigate('/')}
          className={`flex flex-col items-center justify-center flex-1 h-full text-[11px] font-medium transition-colors ${
            currentPath === '/' ? 'text-accent' : 'text-text-tertiary'
          }`}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </button>
        <button
          type="button"
          onClick={() => navigate(firstCasePath)}
          className={`flex flex-col items-center justify-center flex-1 h-full text-[11px] font-medium transition-colors ${
            currentPath.startsWith('/cases') ? 'text-accent' : 'text-text-tertiary'
          }`}
        >
          <FileText size={18} />
          <span>Cases</span>
        </button>
        <button
          type="button"
          onClick={() => navigate('/approvals')}
          className={`flex flex-col items-center justify-center flex-1 h-full text-[11px] font-medium transition-colors ${
            currentPath.startsWith('/approvals') ? 'text-accent' : 'text-text-tertiary'
          }`}
        >
          <CheckSquare size={18} />
          <span>Approvals</span>
        </button>
        <button
          type="button"
          onClick={() => navigate('/benchmark')}
          className={`flex flex-col items-center justify-center flex-1 h-full text-[11px] font-medium transition-colors ${
            currentPath.startsWith('/benchmark') ? 'text-accent' : 'text-text-tertiary'
          }`}
        >
          <BarChart2 size={18} />
          <span>Benchmark</span>
        </button>
        <button
          type="button"
          onClick={() => setIsMobileMenuOpen(true)}
          className="flex flex-col items-center justify-center flex-1 h-full text-[11px] font-medium text-text-tertiary"
        >
          <Menu size={18} />
          <span>More</span>
        </button>
      </nav>

      {/* Mobile Drawer (More options) */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/40" onClick={() => setIsMobileMenuOpen(false)} />
          <div className="relative ml-auto w-64 bg-surface h-full p-6 shadow-lg border-l border-border flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
                <span className="font-semibold text-[14px]">Navigation</span>
                <button type="button" onClick={() => setIsMobileMenuOpen(false)}>
                  <X size={18} />
                </button>
              </div>
              <div className="space-y-2">
                {navLinks.map(l => (
                  <button
                    key={l.path}
                    type="button"
                    onClick={() => {
                      navigate(l.path);
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full text-left py-2 px-3 text-[13px] rounded hover:bg-subtle"
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="pt-4 border-t border-border-subtle">
              <Button size="sm" variant="secondary" className="w-full" onClick={toggleTheme}>
                Toggle {theme === 'light' ? 'Dark' : 'Light'} Mode
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Global Modals & Overlay Drawers */}
      <CommandPalette />
      <EvidenceDrawer />
      <ToastContainer />
    </div>
  );
};
