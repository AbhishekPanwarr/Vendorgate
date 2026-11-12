import React, { useState, useRef } from 'react';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  side = 'top',
  className = ''
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, 180);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  const handleFocus = () => {
    // 0ms delay on focus for a11y
    setIsVisible(true);
  };

  const handleBlur = () => {
    setIsVisible(false);
  };

  const positions = {
    top: 'bottom-[calc(100%+6px)] left-1/2 -translate-x-1/2',
    bottom: 'top-[calc(100%+6px)] left-1/2 -translate-x-1/2',
    left: 'right-[calc(100%+6px)] top-1/2 -translate-y-1/2',
    right: 'left-[calc(100%+6px)] top-1/2 -translate-y-1/2',
  };

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {React.cloneElement(children, {
        'aria-describedby': isVisible ? 'tooltip-content' : undefined,
      } as React.HTMLAttributes<HTMLElement>)}

      {isVisible && content && (
        <div
          id="tooltip-content"
          role="tooltip"
          className={`absolute z-50 px-2.5 py-1.5 text-[12px] leading-tight font-normal text-text-primary bg-surface border border-border-strong rounded-[6px] shadow-md dark:shadow-none max-w-[280px] pointer-events-none whitespace-normal select-none animate-in fade-in-0 zoom-in-95 duration-120 ${positions[side]} ${className}`}
        >
          {content}
        </div>
      )}
    </div>
  );
};
