import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { OperatorPage } from './components/OperatorPage.tsx'

const isOperatorView = typeof window !== 'undefined' && window.location.pathname === '/operator'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isOperatorView ? <OperatorPage /> : <App />}
  </StrictMode>,
)
