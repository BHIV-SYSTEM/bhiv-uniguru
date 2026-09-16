import React, { useEffect, useRef, useState } from 'react';
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
  text = "Continue with Google",
  disabled = false,
  className = ""
}) => {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [, setShowFallback] = useState(false);

  useEffect(() => {
    // Set a timeout to show fallback button if Google script takes too long
    const fallbackTimeout = setTimeout(() => {
      if (!scriptLoaded) {
        setShowFallback(true);
      }
    }, 3000); // Show fallback after 3 seconds

    const loadGoogleScript = () => {
      if (window.google) {
        setScriptLoaded(true);
        setShowFallback(false);
        initializeGoogleSignIn();
        clearTimeout(fallbackTimeout);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setScriptLoaded(true);
        setShowFallback(false);
        clearTimeout(fallbackTimeout);
        initializeGoogleSignIn();
      };
      script.onerror = () => {
        console.error('Failed to load Google Identity Services');
        setShowFallback(true);
        clearTimeout(fallbackTimeout);
        onError?.(new Error('Failed to load Google authentication'));
      };
      document.head.appendChild(script);
    };

    const initializeGoogleSignIn = () => {
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      
      if (!clientId || clientId === "your-google-client-id-here") {
        console.warn("Google Client ID not configured");
        return;
      }

      if (window.google && buttonRef.current) {
        // Prevent duplicate initialization (common in React StrictMode / remounts).
        if (window.__googleGsiInitialized) {
          return;
        }

        // Set up the callback function
        window.googleSignInCallback = (response: any) => {
          setIsLoading(false);
          if (response.credential) {
            onSuccess(response.credential);
          } else {
            onError?.(new Error('No credential received from Google'));
          }
        };

        try {
          // Initialize Google Sign-In with FedCM support
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: window.googleSignInCallback,
            auto_select: false,
            cancel_on_tap_outside: true,
            // Disable FedCM in local/dev to avoid token retrieval abort/network errors.
            use_fedcm_for_prompt: false,
          });
          window.__googleGsiInitialized = true;
        } catch (error) {
          console.error('Error initializing Google Sign-In:', error);
          onError?.(error);
        }
      }
    };

    loadGoogleScript();

    return () => {
      // Cleanup
      clearTimeout(fallbackTimeout);
      if ((window as any).googleSignInCallback) {
        delete (window as any).googleSignInCallback;
      }
    };
  }, [onSuccess, onError]);

  const handleManualSignIn = () => {
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

    if (window.google && scriptLoaded) {
      try {
        // Trigger Google Sign-In prompt
        window.google.accounts.id.prompt((notification: any) => {
          toast.dismiss("google-signin");
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            setIsLoading(false);
            toast.error("Google Sign-In skipped/blocked. Ensure you're signed into Google in this browser and retry.", {
              duration: 3000,
            });
          }
        });
      } catch (error) {
        toast.dismiss("google-signin");
        setIsLoading(false);
        console.error("Google Sign-In error:", error);
        onError?.(error);
      }
    } else {
      // If Google script isn't loaded yet, wait a bit and try again
      setTimeout(() => {
        if (window.google) {
          try {
            window.google.accounts.id.prompt((notification: any) => {
              toast.dismiss("google-signin");
              if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                setIsLoading(false);
                toast.error("Google Sign-In was cancelled or blocked", {
                  duration: 3000,
                });
              }
            });
          } catch (error) {
            toast.dismiss("google-signin");
            setIsLoading(false);
            console.error("Google Sign-In error:", error);
            onError?.(error);
          }
        } else {
          toast.dismiss("google-signin");
          setIsLoading(false);
          toast.error("Google Sign-In is not available", {
            duration: 3000,
          });
        }
      }, 1000);
    }
  };

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const isConfigured = clientId && clientId !== "your-google-client-id-here";

  if (!isConfigured) {
    return (
      <button
        type="button"
        onClick={() => {
          toast.custom((t) => (
            <div className={`${t.visible ? 'animate-enter' : 'animate-leave'} max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5`}>
              <div className="flex-1 w-0 p-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="ml-3 flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      Google OAuth Setup Required
                    </p>
                    <p className="mt-1 text-sm text-gray-500">
                      Configure VITE_GOOGLE_CLIENT_ID in environment variables to enable Google authentication.
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex border-l border-gray-200">
                <button
                  onClick={() => toast.dismiss(t.id)}
                  className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-sm font-medium text-indigo-600 hover:text-indigo-500"
                >
                  OK
                </button>
              </div>
            </div>
          ), { duration: 5000 });
        }}
        disabled={disabled}
        className={`
          w-full flex items-center justify-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3
          border border-gray-600 rounded-lg bg-white hover:bg-gray-50
          text-gray-900 font-medium transition-all duration-200
          disabled:opacity-50 disabled:cursor-not-allowed
          focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900
          ${className}
        `}
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        <span className="text-xs sm:text-sm font-medium">{text} (Setup Required)</span>
      </button>
    );
  }

  // Always use our custom button for better visibility and control
  return (
    <div className={`w-full ${className}`}>
      {/* Hidden Google button container for initialization only */}
      <div
        ref={buttonRef}
        className="hidden"
        style={{ minHeight: '0px' }}
      />

      {/* Custom Google button that's always visible */}
      <button
        type="button"
        onClick={handleManualSignIn}
        disabled={disabled || isLoading}
        className="w-full flex items-center justify-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 border border-gray-600 rounded-lg bg-white hover:bg-gray-50 text-gray-900 font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900"
      >
        {isLoading ? (
          <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
        ) : (
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
        )}
        <span className="text-xs sm:text-sm font-medium">
          {isLoading ? "Loading..." : text}
        </span>
      </button>
    </div>
  );
};

export default GoogleOAuthProduction;
