import React, { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';

interface GoogleOAuthModernProps {
  onSuccess: (credential: string) => void;
  onError?: (error: any) => void;
  disabled?: boolean;
  className?: string;
  buttonText?: string;
}

declare global {
  interface Window {
    google: any;
    IdentityCredential?: any;
    PublicKeyCredential?: any;
  }
}

const GoogleOAuthModern: React.FC<GoogleOAuthModernProps> = ({
  onSuccess,
  onError,
  disabled = false,
  className = "",
  buttonText = "Continue with Google"
}) => {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [fedCMSupported, setFedCMSupported] = useState(false);

  useEffect(() => {
    // Check for FedCM support
    const checkFedCMSupport = () => {
      const hasFedCM = 'IdentityCredential' in window && 'navigator' in window && 'credentials' in navigator;
      setFedCMSupported(hasFedCM);
      console.log('FedCM supported:', hasFedCM);
    };

    checkFedCMSupport();
  }, []);

  useEffect(() => {
    const loadGoogleScript = () => {
      if (scriptLoaded) return;

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setScriptLoaded(true);
        initializeGoogleSignIn();
      };
      script.onerror = () => {
        console.error('Failed to load Google Identity Services');
        onError?.(new Error('Failed to load Google authentication'));
      };
      document.head.appendChild(script);
    };

    const initializeGoogleSignIn = () => {
      if (!window.google || !buttonRef.current) return;

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

      try {
        // Initialize with modern configuration
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
          // Enable FedCM if supported
          use_fedcm_for_prompt: fedCMSupported,
          // Additional FedCM configuration
          ...(fedCMSupported && {
            fedcm_config: {
              mode: 'button',
              mediation: 'optional'
            }
          })
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

      } catch (error) {
        console.error('Error initializing Google Sign-In:', error);
        onError?.(error);
      }
    };

    const handleCredentialResponse = (response: any) => {
      setIsLoading(false);
      if (response.credential) {
        onSuccess(response.credential);
      } else {
        console.error('No credential received from Google');
        onError?.(new Error('No credential received from Google'));
      }
    };

    if (!window.google) {
      loadGoogleScript();
    } else if (scriptLoaded) {
      initializeGoogleSignIn();
    }

    return () => {
      // Cleanup
      setIsLoading(false);
    };
  }, [scriptLoaded, fedCMSupported, onSuccess, onError]);

  const handleManualSignIn = async () => {
    if (disabled || isLoading) return;

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

    if (!clientId || clientId === "your-google-client-id-here") {
      toast.error("Google OAuth is not configured", {
        duration: 3000,
        icon: '⚙️'
      });
      return;
    }

    setIsLoading(true);
    toast.loading("Opening Google Sign-In...", { id: "google-signin" });

    try {
      if (fedCMSupported && window.IdentityCredential) {
        // Try FedCM first
        try {
          const credential = await navigator.credentials.get({
            identity: {
              providers: [{
                configURL: `https://accounts.google.com/.well-known/web-identity`,
                clientId: clientId,
                nonce: Math.random().toString(36).substring(2, 15)
              }]
            }
          } as any);

          if (credential) {
            toast.dismiss("google-signin");
            onSuccess((credential as any).token);
            return;
          }
        } catch (fedcmError) {
          console.log('FedCM failed, falling back to GSI:', fedcmError);
        }
      }

      // Fallback to traditional GSI
      if (window.google && scriptLoaded) {
        window.google.accounts.id.prompt((notification: any) => {
          toast.dismiss("google-signin");
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            setIsLoading(false);
            toast.error("Google Sign-In was cancelled or blocked", {
              duration: 3000,
            });
          }
        });
      } else {
        throw new Error("Google Sign-In not available");
      }
    } catch (error) {
      toast.dismiss("google-signin");
      setIsLoading(false);
      console.error("Google Sign-In error:", error);
      onError?.(error);
    }
  };

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const isConfigured = clientId && clientId !== "your-google-client-id-here";

  if (!isConfigured) {
    return (
      <div className={`w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-gray-400 text-center ${className}`}>
        Google OAuth not configured
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      {/* Google-rendered button */}
      <div ref={buttonRef} className="w-full" />
      
      {/* Fallback manual button */}
      {scriptLoaded && (
        <button
          onClick={handleManualSignIn}
          disabled={disabled || isLoading}
          className="mt-2 w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Signing in...
            </>
          ) : (
            <>
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {buttonText}
            </>
          )}
        </button>
      )}
      
      {fedCMSupported && (
        <div className="mt-1 text-xs text-green-400 text-center">
          ✓ Enhanced security with FedCM
        </div>
      )}
    </div>
  );
};

export default GoogleOAuthModern;
