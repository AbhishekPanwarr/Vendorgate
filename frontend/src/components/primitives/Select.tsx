import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  secondary?: string;
}

export interface SelectProps {
  label?: string;
  helperText?: string;
  error?: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  helperText,
  error,
  options,
  value,
  onChange,
  placeholder = 'Select an option…',
  disabled = false,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const selectedOption = options.find(o => o.value === value);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    if (!isOpen) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        setIsOpen(true);
        const currentIndex = options.findIndex(o => o.value === value);
        setHighlightedIndex(currentIndex >= 0 ? currentIndex : 0);
      }
      return;
    }

    if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex(prev => (prev + 1) % options.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(prev => (prev - 1 + options.length) % options.length);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (options[highlightedIndex]) {
        onChange(options[highlightedIndex].value);
        setIsOpen(false);
      }
    }
  };

  return (
    <div className={`flex flex-col gap-1.5 w-full relative ${className}`} ref={containerRef}>
      {label && (
        <span className="text-[13px] font-medium text-text-primary select-none">
          {label}
        </span>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={`h-9 w-full flex items-center justify-between rounded-[6px] border bg-surface px-3 text-[13px] text-left transition-colors duration-60 focus-ring cursor-pointer disabled:bg-subtle disabled:text-text-tertiary disabled:cursor-not-allowed ${
          error
            ? 'border-danger'
            : 'border-border hover:border-border-strong'
        } ${selectedOption ? 'text-text-primary' : 'text-text-tertiary'}`}
      >
        <span className="truncate">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          size={16}
          className={`text-text-tertiary shrink-0 ml-2 transition-transform duration-120 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute top-[calc(100%+4px)] left-0 w-full z-50 rounded-[12px] border border-border bg-surface shadow-md dark:shadow-none overflow-hidden max-h-60 overflow-y-auto">
          <ul
            ref={listRef}
            role="listbox"
            tabIndex={-1}
            className="p-1 space-y-0.5"
          >
            {options.map((option, idx) => {
              const isSelected = option.value === value;
              const isHighlighted = idx === highlightedIndex;

              return (
                <li
                  key={option.value}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  className={`h-9 px-3 flex items-center justify-between rounded-[6px] text-[13px] cursor-pointer transition-colors duration-60 select-none ${
                    isHighlighted ? 'bg-subtle text-text-primary' : 'text-text-secondary'
                  } ${
                    isSelected ? 'border-l-2 border-accent font-medium text-text-primary bg-accent-subtle/50' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="truncate">{option.label}</span>
                    {option.secondary && (
                      <span className="text-[12px] text-text-tertiary">
                        {option.secondary}
                      </span>
                    )}
                  </div>
                  {isSelected && (
                    <Check size={14} className="text-accent shrink-0 ml-2" />
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {error ? (
        <p role="alert" className="text-[12px] text-danger font-normal">
          {error}
        </p>
      ) : helperText ? (
        <p className="text-[12px] text-text-secondary font-normal">
          {helperText}
        </p>
      ) : null}
    </div>
  );
};
