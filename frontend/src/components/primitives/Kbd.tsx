import React from 'react';

export interface KbdProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
}

export const Kbd: React.FC<KbdProps> = ({ children, className = '', ...props }) => {
  return (
    <kbd
      className={`inline-flex items-center justify-center h-5 px-1.5 text-[11px] font-mono text-text-secondary bg-subtle border border-border rounded-[4px] shadow-xs select-none ${className}`}
      {...props}
    >
      {children}
    </kbd>
  );
};
