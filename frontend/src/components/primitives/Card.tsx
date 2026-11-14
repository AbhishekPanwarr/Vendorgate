import React from 'react';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
  padding?: 'compact' | 'default' | 'hero' | 'none';
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  footer,
  padding = 'default',
  children,
  className = '',
  ...props
}) => {
  const paddings = {
    none: 'p-0',
    compact: 'p-5', // 20px
    default: 'p-6', // 24px
    hero: 'p-8',    // 32px
  };

  return (
    <div
      className={`rounded-[8px] border border-border bg-surface text-text-primary transition-shadow duration-120 hover:shadow-sm dark:hover:shadow-none ${className}`}
      {...props}
    >
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <div>
            {title && (
              <h3 className="text-[18px] font-semibold text-text-primary tracking-[-0.01em] leading-snug">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-[12px] text-text-secondary mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}

      <div className={padding !== 'none' ? paddings[padding] : ''}>
        {children}
      </div>

      {footer && (
        <div className="border-t border-border-subtle px-5 py-3.5 bg-subtle/30 rounded-b-[8px] flex items-center justify-between">
          {footer}
        </div>
      )}
    </div>
  );
};
