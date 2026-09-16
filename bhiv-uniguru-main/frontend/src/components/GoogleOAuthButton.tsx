import React, { useEffect, useRef } from 'react';

interface GoogleOAuthButtonProps {
  onSuccess: (credential: string) => void;
  onError?: (error: any) => void;
  disabled?: boolean;
  className?: string;
}

declare global {
  interface Window {
    google: any;
    googleOneTapCallback: (response: any) => void;
    IdentityCredential?: any;
  }
}

const GoogleOAuthButton: React.FC<GoogleOAuthButtonProps> = ({
  onSuccess,
  onError,
  disabled = false,
  className = ""
}) => {
  const buttonRef = useRef<HTMLDivElement>(null);
  const scriptLoaded = useRef(false);

  useEffect(() => {
    const loadGoogleScript = () => {
      if (scriptLoaded.current) return;

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleSignIn;
      document.head.appendChild(script);
      scriptLoaded.current = true;
    };

    const initializeGoogleSignIn = () => {
      if (window.google && buttonRef.current) {
        // Set up the callback function
        window.googleOneTapCallback = (response: any) => {
          if (response.credential) {
            onSuccess(response.credential);
          } else {
            onError?.(new Error('No credential received'));
          }
        };

        // Get the Google Client ID from environment
        const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

        if (!clientId || clientId === "your-google-client-id-here") {
          console.warn("Google Client ID not configured properly");
          if (buttonRef.current) {
            buttonRef.current.innerHTML = `
              <div class="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-gray-400 text-center">
                Google OAuth not configured
              </div>
            `;
          }
          return;
        }

        // Initialize Google Sign-In with FedCM support
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: window.googleOneTapCallback,
          auto_select: false,
          cancel_on_tap_outside: true,
          // FedCM can fail in local/dev browser setups with aborted token requests.
          // Use classic popup flow for more reliable local development behavior.
          use_fedcm_for_prompt: false,
        });

        // Render the button
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          logo_alignment: 'left',
          width: '100%',
        });
      }
    };

    if (!window.google) {
      loadGoogleScript();
    } else {
      initializeGoogleSignIn();
    }

    return () => {
      // Cleanup
      if ((window as any).googleOneTapCallback) {
        delete (window as any).googleOneTapCallback;
      }
    };
  }, [onSuccess, onError]);

  return (
    <div className={`w-full ${className}`}>
      <div 
        ref={buttonRef} 
        className={`w-full ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
        style={{ minHeight: '44px' }}
      />
      {disabled && (
        <div className="absolute inset-0 bg-gray-900/50 rounded-lg flex items-center justify-center">
          <div className="text-white text-sm">Loading...</div>
        </div>
      )}
    </div>
  );
};

export default GoogleOAuthButton;
