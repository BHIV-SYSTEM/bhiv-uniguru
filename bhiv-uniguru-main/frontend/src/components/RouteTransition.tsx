import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import LoadingSpinner from './LoadingSpinner';
import StarsCanvas from './StarBackground';

interface RouteTransitionProps {
  children: React.ReactNode;
  duration?: number;
}

const RouteTransition: React.FC<RouteTransitionProps> = ({ 
  children, 
  duration = 300 
}) => {
  const location = useLocation();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [displayLocation, setDisplayLocation] = useState(location);

  useEffect(() => {
    if (location !== displayLocation) {
      setIsTransitioning(true);
      
      const timer = setTimeout(() => {
        setDisplayLocation(location);
        setIsTransitioning(false);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [location, displayLocation, duration]);

  if (isTransitioning) {
    return (
      <div className="fixed inset-0 z-50 bg-black/90">
        <div className="fixed inset-0 z-0">
          <StarsCanvas />
        </div>
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="bg-glass-card backdrop-blur-xl rounded-xl p-6 border border-glass-border shadow-glass">
            <LoadingSpinner 
              size="large" 
              variant="orbit" 
              text="Loading..." 
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div key={displayLocation.pathname} className="animate-fade-in">
      {children}
    </div>
  );
};

export default RouteTransition;
