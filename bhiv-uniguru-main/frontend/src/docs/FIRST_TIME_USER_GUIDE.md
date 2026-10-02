# First-Time User Guide Implementation

## Overview
This document describes how to implement a UI helper/notification system to guide first-time users through the guru creation process in the UniGuru application.

## Components Created

### 1. FirstTimeUserGuide Component
Location: `src/components/FirstTimeUserGuide.tsx`

A reusable component that provides:
- Welcome modal for first-time users
- Step-by-step instructions
- Contextual hints in forms
- Visual indicators

### 2. First-Time User Hook
Location: `src/hooks/useFirstTimeUser.ts`

A custom React hook that:
- Detects if a user is visiting for the first time
- Provides functionality to mark users as returning users

### 3. Helper Functions
Location: `src/helpers/firstTimeUserHelper.ts`

Utility functions for:
- Checking if a user is first-time
- Marking users as returning users

### 4. CSS Styles
Location: `src/styles/first-time-user.css`

Styles for:
- Visual indicators (pulsing dot)
- Tooltips
- Welcome modal
- Step-by-step guides

## Implementation Steps

### 1. Import Dependencies
Add the following imports to `src/components/LeftSidebar.tsx`:

```typescript
import FirstTimeUserGuide from "./FirstTimeUserGuide";
import { useFirstTimeUser } from "../hooks/useFirstTimeUser";
import { isFirstTimeUser, markAsReturningUser } from "../helpers/firstTimeUserHelper";
import "../styles/first-time-user.css";
```

### 2. Add First-Time User State
In the LeftSidebar component, add:

```typescript
const { isFirstTimeUser, markAsReturningUser } = useFirstTimeUser();
```

### 3. Show Welcome Toast
Add this useEffect to show a welcome message for first-time users:

```typescript
useEffect(() => {
  if (isFirstTimeUser && gurus.length === 0) {
    toast.success("Welcome! Let's create your first guru to get started 🧙‍♂️", {
      duration: 8000,
      icon: '👋'
    });
  }
}, [isFirstTimeUser, gurus.length]);
```

### 4. Modify Guru Creation Success Message
Update the handleCreateGuru function to show a special message for first-time users:

```typescript
// In the handleCreateGuru function, replace the success toast with:
if (isFirstTimeUser()) {
  markAsReturningUser();
  toast.success("Guru created successfully! Now start a chat with your new guru 🎉", {
    id: "create-guru",
    duration: 6000,
    icon: '✨'
  });
} else {
  toast.success("Guru created successfully! 🧙‍♂️", {
    id: "create-guru",
    icon: '✨'
  });
}
```

### 5. Add First-Time User Guide Component
In the JSX, add the FirstTimeUserGuide component where appropriate:

```tsx
{/* Add this where you want to show the first-time user guide */}
<FirstTimeUserGuide 
  onCreateGuruClick={() => setShowCreateForm(true)}
  showCreateForm={showCreateForm}
  formData={formData}
/>
```

### 6. Add Contextual Hints in the Form
In the guru creation form, add contextual hints:

```tsx
{/* In the name input field */}
{isFirstTimeUser && gurus.length === 0 && !formData.name && (
  <p className="text-yellow-300 text-xs mt-1">← Give your guru a name (e.g., "Math Tutor")</p>
)}

{/* In the subject input field */}
{isFirstTimeUser && gurus.length === 0 && formData.name && !formData.subject && (
  <p className="text-yellow-300 text-xs mt-1">← What subject will your guru specialize in?</p>
)}

{/* In the description textarea */}
{isFirstTimeUser && gurus.length === 0 && formData.name && formData.subject && !formData.description && (
  <p className="text-yellow-300 text-xs mt-1">← Add a brief description of your guru's personality</p>
)}
```

### 7. Add Visual Indicator
Add a visual indicator to draw attention to the create form:

```tsx
{/* Add this to the create form container when it's for a first-time user */}
{isFirstTimeUser && gurus.length === 0 && (
  <div className="absolute -top-2 -right-2">
    <div className="relative">
      <div className="w-4 h-4 bg-yellow-400 rounded-full animate-ping absolute"></div>
      <div className="w-4 h-4 bg-yellow-400 rounded-full relative"></div>
    </div>
  </div>
)}
```

## User Experience Flow

1. **First-time user detection**: When a user visits the app for the first time, they are identified through localStorage.

2. **Welcome message**: A toast notification welcomes the user and explains the next steps.

3. **Welcome modal**: A modal appears with step-by-step instructions on how to create a guru.

4. **Contextual guidance**: As the user fills out the form, contextual hints appear to guide them.

5. **Visual indicators**: A pulsing dot draws attention to the create form.

6. **Success feedback**: After creating their first guru, the user receives special feedback and is marked as a returning user.

7. **Normal experience**: On subsequent visits, users see the normal interface without the guides.

## Technical Details

### LocalStorage Keys
- `uniguru_first_time_user`: Set to 'false' when a user creates their first guru

### CSS Classes
- `first-time-highlight`: Adds a pulsing indicator
- `first-time-tooltip`: Shows contextual hints
- `first-time-modal`: Styles for the welcome modal

### Toast Messages
- Welcome message for first-time users
- Special success message after first guru creation

## Testing

To test the first-time user experience:
1. Clear localStorage: `localStorage.removeItem('uniguru_first_time_user')`
2. Refresh the page
3. Observe the welcome modal and contextual hints
4. Create a guru and verify the special success message
5. Refresh the page and confirm the guides no longer appear

## Future Enhancements

1. **Multi-step onboarding**: Expand the guide to cover chat creation and other features
2. **Interactive tutorial**: Add clickable elements that guide users through each step
3. **Progress tracking**: Show users their progress through the onboarding process
4. **Customization**: Allow users to skip or revisit the guide