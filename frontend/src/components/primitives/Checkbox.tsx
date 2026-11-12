import React from 'react';
import { Check } from 'lucide-react';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: React.ReactNode;
  description?: React.ReactNode;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, checked, onChange, className = '', id, disabled, ...props }, ref) => {
    const inputId = id || (typeof label === 'string' ? `checkbox-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);

    return (
      <label
        htmlFor={inputId}
        className={`flex items-start gap-2.5 cursor-pointer select-none group ${
          disabled ? 'cursor-not-allowed opacity-60' : ''
        } ${className}`}
      >
        <div className="relative flex items-center justify-center mt-0.5">
          <input
            ref={ref}
            type="checkbox"
            id={inputId}
            checked={checked}
            disabled={disabled}
            onChange={onChange}
            className="sr-only"
            {...props}
          />
          <div
            className={`w-4 h-4 rounded-[4px] border transition-all duration-120 flex items-center justify-center ${
              checked
                ? 'bg-accent border-accent text-white'
                : 'bg-surface border-border hover:border-border-strong group-focus-within:ring-2 group-focus-within:ring-accent group-focus-within:ring-offset-2'
            }`}
          >
            {checked && <Check size={12} strokeWidth={3} className="text-white animate-in zoom-in-75 duration-120" />}
          </div>
        </div>

        {(label || description) && (
          <div className="flex flex-col">
            {label && <span className="text-[13px] font-medium text-text-primary leading-tight">{label}</span>}
            {description && <span className="text-[12px] text-text-secondary leading-normal mt-0.5">{description}</span>}
          </div>
        )}
      </label>
    );
  }
);

Checkbox.displayName = 'Checkbox';
