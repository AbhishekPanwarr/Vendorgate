import React from 'react';
import { Search } from 'lucide-react';
import { Kbd } from './Kbd';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  helperText?: string;
  error?: string;
  variant?: 'text' | 'number' | 'password' | 'search';
  leftIcon?: React.ReactNode;
  rightElement?: React.ReactNode;
  containerClassName?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      helperText,
      error,
      variant = 'text',
      leftIcon,
      rightElement,
      className = '',
      containerClassName = '',
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const inputId = id || (label ? `input-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);
    const isSearch = variant === 'search';
    const isNumber = variant === 'number';

    return (
      <div className={`flex flex-col gap-1.5 w-full ${containerClassName}`}>
        {label && (
          <label
            htmlFor={inputId}
            className="text-[13px] font-medium text-text-primary select-none flex items-center justify-between"
          >
            <span>{label}</span>
          </label>
        )}
        <div className="relative flex items-center w-full">
          {isSearch && !leftIcon && (
            <Search className="absolute left-3 w-4 h-4 text-text-tertiary pointer-events-none" />
          )}
          {leftIcon && !isSearch && (
            <div className="absolute left-3 flex items-center pointer-events-none text-text-tertiary">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
            className={`h-9 w-full rounded-[6px] border bg-surface px-3 text-[13px] text-text-primary placeholder:text-text-tertiary transition-colors duration-60 focus-ring disabled:bg-subtle disabled:text-text-tertiary disabled:cursor-not-allowed ${
              isSearch ? 'pl-9 pr-14' : leftIcon ? 'pl-9' : ''
            } ${rightElement ? 'pr-9' : ''} ${
              isNumber ? 'tabular' : ''
            } ${
              error
                ? 'border-danger focus:border-danger'
                : 'border-border hover:border-border-strong focus:border-accent'
            } ${className}`}
            {...props}
          />

          {isSearch && (
            <div className="absolute right-2.5 flex items-center pointer-events-none">
              <Kbd>⌘K</Kbd>
            </div>
          )}

          {rightElement && !isSearch && (
            <div className="absolute right-2.5 flex items-center">
              {rightElement}
            </div>
          )}
        </div>

        {error ? (
          <p id={`${inputId}-error`} role="alert" className="text-[12px] text-danger font-normal">
            {error}
          </p>
        ) : helperText ? (
          <p id={`${inputId}-helper`} className="text-[12px] text-text-secondary font-normal">
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';
