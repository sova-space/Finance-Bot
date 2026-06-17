import type { ReactNode } from 'react';

interface CardProps {
  title?: string;
  tone?: 'default' | 'warning' | 'danger' | 'success';
  children: ReactNode;
}

export function Card({ title, tone = 'default', children }: CardProps) {
  return (
    <section className={`card card-${tone}`}>
      {title ? <h3>{title}</h3> : null}
      {children}
    </section>
  );
}
