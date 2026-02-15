/**
 * =============================================================================
 * MAIN.TSX — Application entry point
 * =============================================================================
 *
 * Mounts the root React component (App) into #root with StrictMode.
 * Global styles are imported from index.css.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
