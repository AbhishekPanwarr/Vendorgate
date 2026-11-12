import React from 'react';

export interface ProgressBarProps {
  progress?: number; // 0 to 100
  indeterminate?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress = 0,
  indeterminate = false,
  className = '',
}) => {
  return (
    <div
      role="progressbar"
      aria-valuenow={indeterminate ? undefined : progress}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`h-1 w-full overflow-hidden rounded-full bg-subtle relative ${className}`}
    >
      {indeterminate ? (
        <div className="absolute top-0 bottom-0 left-0 w-1/3 bg-accent rounded-full animate-[progress_1.4s_ease-in-out_infinite]" />
      ) : (
        <div
          className="h-full bg-accent rounded-full transition-all duration-240 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      )}
    </div>
  );
};
