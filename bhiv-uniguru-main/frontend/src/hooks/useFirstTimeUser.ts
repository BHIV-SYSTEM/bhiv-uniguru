import { useState, useEffect } from "react";

export const useFirstTimeUser = () => {
  const [isFirstTimeUser, setIsFirstTimeUser] = useState(true);

  useEffect(() => {
    try {
      const firstTime = localStorage.getItem('uniguru_first_time_user');
      setIsFirstTimeUser(firstTime === null);
    } catch {
      setIsFirstTimeUser(true);
    }
  }, []);

  const markAsReturningUser = () => {
    try {
      localStorage.setItem('uniguru_first_time_user', 'false');
      setIsFirstTimeUser(false);
    } catch (err) {
      console.warn('Failed to save first-time user status:', err);
    }
  };

  return { isFirstTimeUser, markAsReturningUser };
};