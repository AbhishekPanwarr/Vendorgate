import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  MinusCircle,
  ShieldAlert,
  ShieldCheck,
  Shield,
  Circle
} from 'lucide-react';
import type { StatusType, TierType } from '../../types';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'status' | 'tier' | 'generic';
  status?: StatusType | string;
  tier?: TierType | string;
  color?: 'accent' | 'neutral' | 'danger' | 'warning' | 'success' | 'info';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'generic',
  status,
  tier,
  color = 'neutral',
  size = 'md',
  icon,
  children,
  className = '',
  ...props
}) => {
  // Sizes: sm (20px, 11px), md (24px, 12px), lg (28px, 13px)
  const sizes = {
    sm: 'h-5 px-1.5 text-[11px] gap-1',
    md: 'h-6 px-2 text-[12px] gap-1.5',
    lg: 'h-7 px-2.5 text-[13px] gap-2',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  const currentIconSize = iconSizes[size];

  let displayLabel = children;
  let displayIcon = icon;
  let styleClasses = '';

  if (variant === 'status' || status) {
    const s = (status || children || '').toString().toUpperCase();
    displayLabel = s;

    if (s === 'APPROVED' || s === 'PASS') {
      styleClasses = 'bg-success-subtle text-success border border-success/20';
      displayIcon = <CheckCircle2 size={currentIconSize} className="shrink-0" />;
    } else if (s === 'PENDING' || s === 'WARN') {
      styleClasses = 'bg-warning-subtle text-warning border border-warning/20';
      displayIcon = (
        <span className="relative flex items-center justify-center">
          <Circle size={currentIconSize} className="fill-warning text-warning pending-dot-pulse shrink-0" />
        </span>
      );
    } else if (s === 'REJECTED' || s === 'FAIL') {
      styleClasses = 'bg-danger-subtle text-danger border border-danger/20';
      displayIcon = <XCircle size={currentIconSize} className="shrink-0" />;
    } else if (s === 'UNVERIFIABLE' || s === 'INFO') {
      styleClasses = 'bg-info-subtle text-info border border-info/20';
      displayIcon = <HelpCircle size={currentIconSize} className="shrink-0" />;
    } else if (s === 'BLOCKED' || s === 'SKIPPED') {
      styleClasses = 'bg-subtle text-neutral-strong border border-border-strong/40';
      displayIcon = <MinusCircle size={currentIconSize} className="shrink-0" />;
    } else {
      styleClasses = 'bg-subtle text-secondary border border-border';
      displayIcon = <Circle size={currentIconSize} className="shrink-0" />;
    }
  } else if (variant === 'tier' || tier) {
    const t = (tier || children || '').toString().toUpperCase();
    displayLabel = `Tier: ${t}`;

    if (t === 'LOW') {
      styleClasses = 'bg-success-subtle text-success border border-success/20';
      displayIcon = <ShieldCheck size={currentIconSize} className="shrink-0" />;
    } else if (t === 'MEDIUM') {
      styleClasses = 'bg-warning-subtle text-warning border border-warning/20';
      displayIcon = <Shield size={currentIconSize} className="shrink-0" />;
    } else if (t === 'HIGH' || t === 'BLOCKED') {
      styleClasses = 'bg-danger-subtle text-danger border border-danger/20';
      displayIcon = <ShieldAlert size={currentIconSize} className="shrink-0" />;
    }
  } else {
    // Generic variant
    const genericMap = {
      accent: 'bg-accent-subtle text-accent-fg border border-accent/20',
      neutral: 'bg-subtle text-secondary border border-border',
      danger: 'bg-danger-subtle text-danger border border-danger/20',
      warning: 'bg-warning-subtle text-warning border border-warning/20',
      success: 'bg-success-subtle text-success border border-success/20',
      info: 'bg-info-subtle text-info border border-info/20',
    };
    styleClasses = genericMap[color] || genericMap.neutral;
  }

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full select-none ${sizes[size]} ${styleClasses} ${className}`}
      {...props}
    >
      {displayIcon}
      <span className="truncate">{displayLabel}</span>
    </span>
  );
};
