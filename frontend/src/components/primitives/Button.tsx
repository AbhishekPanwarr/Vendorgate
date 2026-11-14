import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'secondary',
      size = 'md',
      loading = false,
      disabled = false,
      leftIcon,
      rightIcon,
      children,
      className = '',
      ...props
    },
    ref
  ) => {
    // Base styles
    const base =
      'inline-flex items-center justify-center font-medium rounded-[6px] transition-colors duration-60 focus-ring btn-press cursor-pointer disabled:cursor-not-allowed select-none';

    // Sizes: sm (32px, 12px font, px-3), md (36px, 13px, px-4), lg (44px, 14px, px-5)
    const sizes = {
      sm: 'h-8 px-3 text-[12px] gap-1.5',
      md: 'h-9 px-4 text-[13px] gap-2',
      lg: 'h-11 px-5 text-[14px] gap-2.5',
    };

    // Variants
    const variants = {
      primary:
        'bg-[#4338CA] dark:bg-[#4F46E5] text-white hover:bg-[#3730A3] dark:hover:bg-[#4338CA] disabled:opacity-50',
      secondary:
        'bg-surface border border-border text-primary hover:bg-subtle disabled:bg-subtle disabled:text-tertiary disabled:border-border-subtle shadow-xs dark:shadow-none',
      ghost:
        'bg-transparent text-secondary hover:text-primary hover:bg-subtle disabled:text-tertiary disabled:bg-transparent',
      destructive:
        'bg-danger text-white hover:bg-danger/90 disabled:bg-danger/40',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
        {...props}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin text-current" />
        ) : (
          leftIcon
        )}
        <span>{children}</span>
        {!loading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
