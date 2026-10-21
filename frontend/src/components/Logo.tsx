import { BRAND } from '../lib/constants';

interface LogoProps {
  size?: number;
  variant?: 'full' | 'icon';
  className?: string;
}

export function Logo({ size = 32, variant = 'full', className = '' }: LogoProps) {
  if (variant === 'icon') {
    return (
      <img
        src={BRAND.iconSvg}
        alt={BRAND.name}
        width={size}
        height={size}
        className={className}
      />
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img
        src={BRAND.iconSvg}
        alt=""
        width={size}
        height={size}
        aria-hidden="true"
      />
      <span
        className="font-bold"
        style={{ color: `var(--color-brand, ${BRAND.colorPrimary})` }}
      >
        {BRAND.fullName}
      </span>
    </div>
  );
}
