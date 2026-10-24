import React from 'react';
import { SdgStripe } from '../brand/SdgStripe.jsx';
import { Button } from '../actions/Button.jsx';

/** .one · het tegenbeeld. Licht, eigen sfeer. Eén slotpagina of slotblok. */
export function Tegenbeeld({ kicker = '6GMATRIX.ONE · HET TEGENBEELD', title = 'natuurlijke harmonieën', text, image, cta = 'Verder kijken', onCta, ctaHref, size = 'block' }) {
  const big = size === 'page';
  const H = big ? 'h1' : 'h2'; // als paginakop is dit de h1
  return (
    <section style={{ background: 'var(--paper-1)', color: 'var(--paper-ink)' }}>
      <SdgStripe height={big ? 8 : 5} />
      <div style={{ maxWidth: 'var(--container)', margin: '0 auto', padding: (big ? 'var(--space-9)' : 'var(--space-7)') + ' var(--gutter)', display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,' + (big ? '1fr' : '.6fr') + ')', gap: 'var(--space-7)', alignItems: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <span style={{ font: 'var(--text-label)', letterSpacing: 'var(--track-label)', color: 'var(--paper-mute)' }}>{kicker}</span>
          <H style={{ margin: 0, font: (big ? 'var(--text-h1)' : 'var(--text-h2)'), letterSpacing: 'var(--track-display)' }}>{title}</H>
          {text && <p style={{ margin: 0, font: 'var(--text-lede)', color: 'var(--paper-mute)', maxWidth: 'var(--measure)', textWrap: 'pretty' }}>{text}</p>}
          {cta && <div><Button variant="secondary" tone="paper" onClick={onCta} href={ctaHref}>{cta}</Button></div>}
        </div>
        {image && <div style={{ aspectRatio: big ? '4/3' : '1', borderRadius: big ? 'var(--radius-m)' : '50%', backgroundImage: 'url(' + image + ')', backgroundSize: 'cover', backgroundPosition: 'center', maxWidth: big ? 'none' : 260, width: '100%', justifySelf: 'end' }} />}
      </div>
    </section>
  );
}
