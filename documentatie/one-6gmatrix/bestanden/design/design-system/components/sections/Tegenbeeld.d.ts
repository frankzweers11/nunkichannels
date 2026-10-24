import * as React from 'react';
/**
 * .one · het tegenbeeld: licht, eigen sfeer. Slotblok op de ingang of de slotpagina na het laatste dossier.
 * @startingPoint section="Secties" subtitle=".one · het tegenbeeld (licht)" viewport="700x320"
 */
export interface TegenbeeldProps { kicker?: string; title?: string; text?: string; image?: string; cta?: string; onCta?: () => void; ctaHref?: string; size?: 'block' | 'page'; }
export declare function Tegenbeeld(props: TegenbeeldProps): React.JSX.Element;
