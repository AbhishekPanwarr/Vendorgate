import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  width?: 'default' | 'wide' | 'full';
  headerActions?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  width = 'default',
  headerActions,
  footer,
  children,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widths = {
    default: 'w-full md:w-[480px]',
    wide: 'w-full md:w-[640px]',
    full: 'w-full md:w-[840px]',
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 overflow-hidden"
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/30 dark:bg-black/60 transition-opacity duration-240"
      />

      {/* Drawer panel */}
      <div className="fixed inset-y-0 right-0 flex max-w-full">
        <div
          className={`${widths[width]} bg-surface border-l border-border text-text-primary shadow-lg dark:shadow-none flex flex-col h-full transform transition-transform duration-240 ease-[cubic-bezier(0.25,1,0.5,1)] translate-x-0`}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-border-subtle shrink-0">
            <div className="truncate mr-4">
              <div className="text-[18px] font-semibold text-text-primary tracking-[-0.01em] truncate">
                {title}
              </div>
              {subtitle && (
                <div className="text-[12px] text-text-secondary mt-0.5 truncate">
                  {subtitle}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {headerActions}
              <button
                type="button"
                onClick={onClose}
                aria-label="Close drawer"
                className="w-8 h-8 flex items-center justify-center rounded-[6px] text-text-tertiary hover:text-text-primary hover:bg-subtle transition-colors focus-ring cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="p-6 overflow-y-auto flex-1 space-y-6">
            {children}
          </div>

          {/* Sticky Footer */}
          {footer && (
            <div className="p-4 px-6 border-t border-border-subtle bg-surface sticky bottom-0 z-10 flex items-center justify-between">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
