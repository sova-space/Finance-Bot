import type { ReactNode } from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  tone?: 'default' | 'warning' | 'danger' | 'success' | 'accent' | 'dark';
  className?: string;
  children: ReactNode;
}

export function Card({ title, subtitle, tone = 'default', className = '', children }: CardProps) {
  return (
    <section className={`card card-${tone} ${className}`.trim()}>
      {title ? (
        <div className="card-head">
          <h3>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
