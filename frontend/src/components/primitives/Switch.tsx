import React from 'react';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  id?: string;
}

export const Switch: React.FC<SwitchProps> = ({ checked, onChange, label, disabled = false, id }) => {
  const switchId = id || (label ? `switch-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);

  return (
    <label
      htmlFor={switchId}
      className={`inline-flex items-center gap-2.5 cursor-pointer select-none ${
        disabled ? 'cursor-not-allowed opacity-60' : ''
      }`}
    >
      <input
        type="checkbox"
        id={switchId}
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
        className="sr-only"
      />
      <div
        className={`w-8 h-5 rounded-full p-0.5 transition-colors duration-120 flex items-center focus-ring ${
          checked ? 'bg-accent' : 'bg-border-strong'
        }`}
      >
        <div
          className={`w-4 h-4 rounded-full bg-white transition-transform duration-120 shadow-xs ${
            checked ? 'translate-x-3' : 'translate-x-0'
          }`}
        />
      </div>
      {label && <span className="text-[13px] font-medium text-text-primary">{label}</span>}
    </label>
  );
};
