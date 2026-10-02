// Helper functions for first-time user experience
export const isFirstTimeUser = (): boolean => {
  try {
    const firstTime = localStorage.getItem('uniguru_first_time_user');
    return firstTime === null;
  } catch {
    return true;
  }
};

export const markAsReturningUser = (): void => {
  try {
    localStorage.setItem('uniguru_first_time_user', 'false');
  } catch (err) {
    console.warn('Failed to save first-time user status:', err);
  }
};

export const showFirstTimeUserToast = () => {
  // This would be called from a component that has access to toast
  // We'll implement the actual toast in the component
};