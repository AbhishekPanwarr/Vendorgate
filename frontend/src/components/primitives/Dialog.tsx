import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { Button } from './Button';

export interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  primaryAction?: {
    label: string;
    onClick: () => void;
    loading?: boolean;
    disabled?: boolean;
    destructive?: boolean;
  };
  cancelLabel?: string;
  destructive?: boolean;
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  size = 'md',
  children,
  primaryAction,
  cancelLabel = 'Cancel',
  destructive = false,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);

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

  const maxSizes = {
    sm: 'max-w-[480px]',
    md: 'max-w-[640px]',
    lg: 'max-w-[800px]',
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (!destructive && dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 dark:bg-black/60 backdrop-blur-[2px] animate-in fade-in-0 duration-180"
    >
      <div
        ref={dialogRef}
        className={`w-full ${maxSizes[size]} rounded-[12px] border border-border bg-surface text-text-primary shadow-lg dark:shadow-none overflow-hidden animate-in zoom-in-95 duration-240 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col max-h-[90vh]`}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 pb-4 border-b border-border-subtle">
          <div>
            <h2 id="dialog-title" className="text-[20px] font-semibold text-text-primary tracking-[-0.01em]">
              {title}
            </h2>
            {description && (
              <p className="text-[13px] text-text-secondary mt-1">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="w-8 h-8 flex items-center justify-center rounded-[6px] text-text-tertiary hover:text-text-primary hover:bg-subtle transition-colors focus-ring"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {children}
        </div>

        {/* Footer */}
        {(primaryAction || cancelLabel) && (
          <div className="flex items-center justify-between p-4 px-6 border-t border-border-subtle bg-subtle/30">
            <div>
              {cancelLabel && (
                <Button variant="ghost" onClick={onClose}>
                  {cancelLabel}
                </Button>
              )}
            </div>
            {primaryAction && (
              <Button
                variant={primaryAction.destructive ? 'destructive' : 'primary'}
                onClick={primaryAction.onClick}
                loading={primaryAction.loading}
                disabled={primaryAction.disabled}
              >
                {primaryAction.label}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
