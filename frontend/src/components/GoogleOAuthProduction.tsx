
import React, { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';

interface GoogleOAuthProductionProps {
  onSuccess: (credential: string) => void;
  onError?: (error: any) => void;
  text?: string;
  disabled?: boolean;
  className?: string;
}

declare global {
  interface Window {
    google: any;
    googleSignInCallback: (response: any) => void;
    __googleGsiInitialized?: boolean;
  }
}

const GoogleOAuthProduction: React.FC<GoogleOAuthProductionProps> = ({
  onSuccess,
  onError,
  text = 'Continue with Google',
  disabled = false,
  className = '',
}) => {
  const buttonRef = useRef<HTMLDivElement>(null);
  const callbacksRef = useRef({ onSuccess, onError });
  const mountedRef = useRef(false);

  // Always use the latest React callbacks.
  useEffect(() => {
    callbacksRef.current = { onSuccess, onError };
  }, [onSuccess, onError]);

  useEffect(() => {
    mountedRef.current = true;

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

    if (!clientId || clientId === 'your-google-client-id-here') {
      console.error('Google Client ID is not configured.');
      toast.error('Google authentication is not configured.');
      return;
    }

    let cancelled = false;

    const handleCredentialResponse = (response: any) => {
      if (!mountedRef.current) return;

      if (response?.credential) {
        callbacksRef.current.onSuccess(response.credential);
      } else {
        const error = new Error(
          'No credential received from Google.'
        );

        callbacksRef.current.onError?.(error);
        toast.error('Google authentication failed.');
      }
    };

    // Google calls this callback after successful sign-in.
    window.googleSignInCallback = handleCredentialResponse;

    const renderGoogleButton = () => {
      if (
        cancelled ||
        !mountedRef.current ||
        !buttonRef.current ||
        !window.google?.accounts?.id
      ) {
        return;
      }

      try {
        // Initialize Google Identity Services only once.
        if (!window.__googleGsiInitialized) {
          window.google.accounts.id.initialize({
            client_id: clientId,

            callback: (response: any) => {
              // Resolve the latest registered callback.
              window.googleSignInCallback?.(response);
            },

            auto_select: false,
            cancel_on_tap_outside: true,

            // We use the actual Google button, not One Tap.
            use_fedcm_for_prompt: false,
          });

          window.__googleGsiInitialized = true;
        }

        // Clear any previously rendered button.
        buttonRef.current.innerHTML = '';

        // Render Google's official Sign-In button.
        window.google.accounts.id.renderButton(
          buttonRef.current,
          {
            type: 'standard',
            theme: 'outline',
            size: 'large',
            text: text.toLowerCase().includes('sign in')
              ? 'signin_with'
              : 'continue_with',
            shape: 'rectangular',
            logo_alignment: 'left',
            width: Math.min(
              buttonRef.current.clientWidth || 350,
              400
            ),
          }
        );

      } catch (error) {
        console.error(
          'Google Sign-In initialization error:',
          error
        );

        callbacksRef.current.onError?.(error);
        toast.error('Unable to initialize Google Sign-In.');
      }
    };

    const loadGoogleScript = () => {
      if (window.google?.accounts?.id) {
        renderGoogleButton();
        return;
      }

      let script = document.querySelector<HTMLScriptElement>(
        'script[src="https://accounts.google.com/gsi/client"]'
      );

      if (!script) {
        script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
      }

      const handleLoad = () => {
        if (!cancelled) {
          renderGoogleButton();
        }
      };

      const handleError = () => {
        if (!cancelled) {
          console.error(
            'Failed to load Google Identity Services.'
          );

          const error = new Error(
            'Failed to load Google authentication.'
          );

          callbacksRef.current.onError?.(error);
          toast.error('Google Sign-In is unavailable. Please retry.');
        }
      };

      script.addEventListener('load', handleLoad);
      script.addEventListener('error', handleError);

      // Handle a script that finished loading before listeners
      // were attached.
      if (window.google?.accounts?.id) {
        renderGoogleButton();
      }

      return () => {
        script?.removeEventListener('load', handleLoad);
        script?.removeEventListener('error', handleError);
      };
    };

    const removeListeners = loadGoogleScript();

    return () => {
      cancelled = true;
      mountedRef.current = false;
      removeListeners?.();
    };
  }, [text]);

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  const isConfigured =
    clientId &&
    clientId !== 'your-google-client-id-here';

  if (!isConfigured) {
    return (
      <button
        type="button"
        disabled
        className={`w-full px-4 py-3 border rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed ${className}`}
        title="Configure VITE_GOOGLE_CLIENT_ID"
      >
        Google Sign-In Not Configured
      </button>
    );
  }

  return (
    <div
      className={`w-full flex justify-center ${className}`}
      style={{
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
      }}
    >
      <div
        ref={buttonRef}
        className="w-full flex justify-center"
        style={{
          minHeight: '44px',
          width: '100%',
        }}
      />
    </div>
  );
};

export default GoogleOAuthProduction;
