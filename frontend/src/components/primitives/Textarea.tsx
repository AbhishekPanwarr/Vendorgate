import React from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  helperText?: string;
  error?: string;
  containerClassName?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      helperText,
      error,
      rows = 3,
      className = '',
      containerClassName = '',
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const inputId = id || (label ? `textarea-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);

    return (
      <div className={`flex flex-col gap-1.5 w-full ${containerClassName}`}>
        {label && (
          <label htmlFor={inputId} className="text-[13px] font-medium text-text-primary select-none">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          rows={rows}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          className={`w-full rounded-[6px] border bg-surface p-3 text-[13px] text-text-primary placeholder:text-text-tertiary transition-colors duration-60 focus-ring disabled:bg-subtle disabled:text-text-tertiary disabled:cursor-not-allowed resize-y ${
            error
              ? 'border-danger focus:border-danger'
              : 'border-border hover:border-border-strong focus:border-accent'
          } ${className}`}
          {...props}
        />
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

Textarea.displayName = 'Textarea';
