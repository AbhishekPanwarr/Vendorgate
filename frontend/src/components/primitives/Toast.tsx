import React from 'react';
import { X, CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useApp();

  if (toasts.length === 0) return null;

  const icons = {
    default: <Info size={16} className="text-accent shrink-0 mt-0.5" />,
    success: <CheckCircle2 size={16} className="text-success shrink-0 mt-0.5" />,
    warning: <AlertTriangle size={16} className="text-warning shrink-0 mt-0.5" />,
    danger: <AlertCircle size={16} className="text-danger shrink-0 mt-0.5" />,
  };

  const borders = {
    default: 'border-border',
    success: 'border-success/30',
    warning: 'border-warning/30',
    danger: 'border-danger/30',
  };

  return (
    <div
      aria-live="polite"
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-[360px] w-full pointer-events-none"
    >
      {toasts.map(toast => {
        const variant = toast.variant || 'default';

        return (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto w-full p-3.5 bg-surface rounded-[8px] border shadow-md dark:shadow-none text-text-primary flex items-start gap-3 transform transition-all duration-180 ease-[cubic-bezier(0.16,1,0.3,1)] ${borders[variant]}`}
          >
            {icons[variant]}
            <div className="flex-1 truncate">
              <div className="text-[13px] font-medium leading-tight">
                {toast.title}
              </div>
              {toast.description && (
                <div className="text-[12px] text-text-secondary mt-1 leading-normal">
                  {toast.description}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              aria-label="Dismiss toast"
              className="text-text-tertiary hover:text-text-primary p-0.5 rounded-[4px] hover:bg-subtle transition-colors shrink-0 cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
