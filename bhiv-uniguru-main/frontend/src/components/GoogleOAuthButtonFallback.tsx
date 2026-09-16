import React, { useState } from 'react';
import toast from 'react-hot-toast';

interface GoogleOAuthButtonFallbackProps {
  onSuccess: (credential: string) => void;
  onError?: (error: any) => void;
  text?: string;
  disabled?: boolean;
  className?: string;
}

const GoogleOAuthButtonFallback: React.FC<GoogleOAuthButtonFallbackProps> = ({
  onSuccess,
  onError,
  text = "Continue with Google",
  disabled = false,
  className = ""
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogleLogin = async () => {
    if (disabled || isLoading) return;

    setIsLoading(true);
    toast.loading("Initializing Google authentication...", { id: "google-auth" });

    try {
      // Check if Google Identity Services is available
      if (window.google && window.google.accounts) {
        const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

        if (!clientId || clientId === "your-google-client-id-here") {
          throw new Error("Google Client ID not configured");
        }

        // Initialize Google Sign-In with FedCM support
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response: any) => {
            toast.dismiss("google-auth");
            if (response.credential) {
              onSuccess(response.credential);
            } else {
              onError?.(new Error('No credential received from Google'));
            }
            setIsLoading(false);
          },
          auto_select: false,
          cancel_on_tap_outside: true,
          // Enable FedCM
          use_fedcm_for_prompt: true,
        });

        // Prompt for Google Sign-In
        window.google.accounts.id.prompt((notification: any) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            // Fallback to popup if prompt is not displayed
            window.google.accounts.oauth2.initTokenClient({
              client_id: clientId,
              scope: 'email profile',
              callback: (response: any) => {
                toast.dismiss("google-auth");
                if (response.access_token) {
                  // You would need to exchange this token for user info
                  // For now, we'll show an error
                  onError?.(new Error('OAuth flow needs additional implementation'));
                } else {
                  onError?.(new Error('Google authentication failed'));
                }
                setIsLoading(false);
              },
            }).requestAccessToken();
          }
        });
      } else {
        // Load Google Identity Services script
        const script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.onload = () => {
          // Retry after script loads
          setTimeout(() => handleGoogleLogin(), 100);
        };
        script.onerror = () => {
          throw new Error('Failed to load Google Identity Services');
        };
        document.head.appendChild(script);
      }
    } catch (error) {
      toast.dismiss("google-auth");
      toast.error("Google authentication is not properly configured", {
        duration: 4000,
        icon: '⚙️'
      });
      onError?.(error);
      setIsLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleGoogleLogin}
      disabled={disabled || isLoading}
      className={`
        w-full flex items-center justify-center gap-3 px-4 py-3 
        border border-gray-600 rounded-lg bg-white hover:bg-gray-50 
        text-gray-900 font-medium transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900
        ${className}
      `}
    >
      {isLoading ? (
        <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
      ) : (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
      )}
      <span className="text-sm font-medium">
        {isLoading ? "Authenticating..." : text}
      </span>
    </button>
  );
};

export default GoogleOAuthButtonFallback;
