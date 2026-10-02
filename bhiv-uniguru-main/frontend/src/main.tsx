import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { GuruProvider } from './context/GuruContext'
import { ChatProvider } from './context/ChatContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <GuruProvider>
          <ChatProvider>
            <App />
          </ChatProvider>
        </GuruProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
