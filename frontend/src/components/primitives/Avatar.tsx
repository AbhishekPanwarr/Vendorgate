import React from 'react';

export interface AvatarProps {
  name: string;
  size?: 24 | 32 | 40;
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({ name, size = 32, className = '' }) => {
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0].toUpperCase())
    .join('');

  const sizes = {
    24: 'w-6 h-6 text-[10px]',
    32: 'w-8 h-8 text-[12px]',
    40: 'w-10 h-10 text-[14px]',
  };

  return (
    <div
      aria-label={name}
      className={`inline-flex items-center justify-center rounded-full bg-subtle text-text-primary font-medium border-2 border-border-subtle shrink-0 select-none ${sizes[size]} ${className}`}
    >
      {initials || 'VG'}
    </div>
  );
};
