# LeftSidebar Component Patch for First-Time User Guide

## Overview
This patch document describes the exact changes needed to implement the first-time user guide functionality in the LeftSidebar component.

## Required Imports

Add these imports at the top of `src/components/LeftSidebar.tsx`:

```typescript
import "../styles/first-time-user.css";
import { showFirstTimeUserWelcome, showFirstGuruCreatedMessage, FirstTimeUserFormGuide, FirstTimeUserWelcomeModal } from "../helpers/firstTimeUserGuide";
```

## State Management

Add this useEffect hook to show the welcome toast for first-time users:

```typescript
// Show first-time user guide
useEffect(() => {
  if (gurus.length === 0) {
    showFirstTimeUserWelcome();
  }
}, [gurus.length]);
```

## Component Modifications

### 1. Update handleCreateGuru function

Replace the success toast in the handleCreateGuru function with:

```typescript
setFormData({ name: "", subject: "", description: "" });
setShowCreateForm(false);

// Show first-time user success message or regular success message
if (!showFirstGuruCreatedMessage()) {
  toast.success("Guru created successfully! 🧙‍♂️", {
    id: "create-guru",
    icon: '✨'
  });
}
```

### 2. Add FirstTimeUserWelcomeModal to JSX

Add this component before the ConfirmationModal:

```tsx
{/* First-time user welcome modal */}
<FirstTimeUserWelcomeModal 
  isVisible={gurus.length === 0 && showCreateForm === false}
  onGetStarted={() => setShowCreateForm(true)}
  onSkip={() => {
    try {
      localStorage.setItem('uniguru_first_time_user', 'false');
    } catch (err) {
      console.warn('Failed to save first-time user status:', err);
    }
  }}
/>
```

### 3. Add FirstTimeUserFormGuide to the create form

In the create form JSX, add the FirstTimeUserFormGuide component:

```tsx
{/* Create New Guru Form */}
{showCreateForm && (
  <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/30 backdrop-blur-sm rounded-xl p-6 border border-purple-400/30 shadow-xl relative">
    <FirstTimeUserFormGuide 
      isFirstTime={(() => {
        try {
          const firstTime = localStorage.getItem('uniguru_first_time_user');
          return firstTime === null;
        } catch {
          return true;
        }
      })()}
      formData={formData}
      gurusLength={gurus.length}
    />
    
    <div className="flex items-center gap-3 mb-6">
      <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
        <img src={guruLogo} alt="Guru" className="w-5 h-5" />
      </div>
      <h3 className="text-white font-semibold text-lg">Create New Guru</h3>
    </div>

    {/* Rest of the form remains the same */}
    <form onSubmit={handleCreateGuru} className="space-y-4">
      {/* ... existing form code ... */}
    </form>
  </div>
)}
```

## User Experience Flow

1. When a user visits the app for the first time with no gurus, they see a welcome toast
2. If they haven't opened the create form yet, they see a welcome modal with instructions
3. When they open the create form, they see contextual hints and a visual indicator
4. After creating their first guru, they see a special success message
5. On subsequent visits, none of these guides appear

## Testing

To test the first-time user experience:
1. Clear localStorage: `localStorage.removeItem('uniguru_first_time_user')`
2. Refresh the page
3. Observe the welcome toast and modal
4. Open the create form and see the contextual hints
5. Create a guru and verify the special success message
6. Refresh and confirm the guides no longer appear

## Benefits

This implementation provides:
- Non-intrusive guidance that can be skipped
- Contextual help that appears when needed
- Visual indicators to draw attention to important elements
- Special feedback for first-time users
- No impact on returning users' experience