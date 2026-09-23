import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { redirectingToSignInDomain } from './lib/firebase'

// On a domain that forwards to the sign-in domain, don't flash the app before the page changes.
if (!redirectingToSignInDomain) {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
