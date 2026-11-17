import React, { useEffect } from 'react';

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'mitra-companion': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & {
        'stylesheet-path'?: string;
        'api-base-url'?: string;
        'host-app'?: string;
      }, HTMLElement>;
    }
  }
}

export const MitraCompanion: React.FC = () => {
  useEffect(() => {
    const SCRIPT_ID = 'mitra-companion-script';
    if (!document.getElementById(SCRIPT_ID)) {
      const script = document.createElement('script');
      script.id = SCRIPT_ID;
      script.type = 'module';
      script.src = 'https://mitra.blackholeinfiverse.com/src/mitra-companion.js';
      document.body.appendChild(script);
    }
  }, []);

  return (
    <mitra-companion 
      stylesheet-path="https://mitra.blackholeinfiverse.com/styles/mitra-companion.css" 
      api-base-url="https://mitra.blackholeinfiverse.com"
      host-app="uniguru"
    />
  );
};

export default MitraCompanion;
