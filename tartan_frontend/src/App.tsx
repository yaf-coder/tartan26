/**
 * =============================================================================
 * APP.TSX - Main Application Component
 * =============================================================================
 * 
 * This is the root component that orchestrates the entire application.
 * 
 * STRUCTURE:
 * - Header with product title
 * - Two-column layout:
 *   - Main area: Chat input, upload zone, loading state, or results
 *   - Sidebar: Status indicators
 * 
 * STATE MACHINE:
 * - idle: Initial state, showing input forms
 * - loading: Processing query, showing progress stepper
 * - results: Showing literature review results
 * - error: Something went wrong (with retry option)
 * =============================================================================
 */

import { useState, useCallback } from 'react';

// Types
import type { AppState, LoadingStep, UploadedFile } from './types';

// Components
import {
  ChatInput,
  UploadDropzone,
  ProgressStepper,
  LiteratureReview,
} from './components';

// Styles
import './App.css';

// Mock Data
import { generateMockSources, generateMockSummary } from './mockData';

// -----------------------------------------------------------------------------
// CONSTANTS
// -----------------------------------------------------------------------------

/** Duration for each loading step (in milliseconds) */
const STEP_DURATION = 1500;

/** All loading steps in order */
const LOADING_STEPS: LoadingStep[] = [
  'finding-sources',
  'extracting-quotes',
  'cross-checking',
  'compiling',
];

// -----------------------------------------------------------------------------
// MAIN APP COMPONENT
// -----------------------------------------------------------------------------

function App() {
  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------

  /** Current app state: idle, loading, results, or error */
  const [appState, setAppState] = useState<AppState>('idle');

  /** The user's research query */
  const [query, setQuery] = useState('');

  /** Uploaded files */
  const [files, setFiles] = useState<UploadedFile[]>([]);

  /** Current loading step (when in loading state) */
  const [currentStep, setCurrentStep] = useState<LoadingStep>('finding-sources');

  // ---------------------------------------------------------------------------
  // HANDLERS
  // ---------------------------------------------------------------------------

  /**
   * Handle query submission
   * This simulates the research process with loading states
   */
  const handleSubmit = useCallback((submittedQuery: string) => {
    // Save the query
    setQuery(submittedQuery);

    // Start loading
    setAppState('loading');
    setCurrentStep('finding-sources');

    // Simulate each loading step
    let stepIndex = 0;

    const advanceStep = () => {
      stepIndex++;

      if (stepIndex < LOADING_STEPS.length) {
        // Move to next step
        setCurrentStep(LOADING_STEPS[stepIndex]);
        setTimeout(advanceStep, STEP_DURATION);
      } else {
        // All steps complete, show results
        setAppState('results');
      }
    };

    // Start the step progression
    setTimeout(advanceStep, STEP_DURATION);
  }, []);

  /**
   * Reset to idle state (start over)
   */
  const handleReset = useCallback(() => {
    setAppState('idle');
    setQuery('');
    setFiles([]);
    setCurrentStep('finding-sources');
  }, []);

  // ---------------------------------------------------------------------------
  // RENDER HELPERS
  // ---------------------------------------------------------------------------

  /**
   * Render the main content area based on current state
   */
  const renderMainContent = () => {
    switch (appState) {
      case 'idle':
        return (
          <div className="app__input-section">
            {/* Chat input */}
            <ChatInput onSubmit={handleSubmit} disabled={false} />

            {/* File upload */}
            <UploadDropzone
              files={files}
              onFilesChange={setFiles}
              disabled={false}
            />
          </div>
        );

      case 'loading':
        return (
          <div className="app__loading-section">
            {/* Show the query being processed */}
            <div className="app__query-display">
              <span className="app__query-label">Researching:</span>
              <p className="app__query-text">"{query}"</p>
            </div>

            {/* Progress stepper */}
            <ProgressStepper currentStep={currentStep} />
          </div>
        );

      case 'results':
        return (
          <div className="app__results-section">
            {/* Show the query that was processed */}
            <div className="app__query-display app__query-display--complete">
              <span className="app__query-label">Research completed for:</span>
              <p className="app__query-text">"{query}"</p>
              <button
                className="app__new-search-btn"
                onClick={handleReset}
              >
                New Search
              </button>
            </div>

            {/* Literature review results - empty until backend is connected */}
            <LiteratureReview
              sources={[]}
              summary="Results will appear here when connected to the backend."
            />
          </div>
        );

      case 'error':
        return (
          <div className="app__error-section">
            <div className="app__error-message">
              <h3>Something went wrong</h3>
              <p>We couldn't complete your research. Please try again.</p>
              <button onClick={handleReset}>Try Again</button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------

  return (
    <div className="app">
      {/* Decorative background elements */}
      <div className="app__bg-orb app__bg-orb--1" aria-hidden="true" />
      <div className="app__bg-orb app__bg-orb--2" aria-hidden="true" />

      {/* Header / Hero */}
      <header className="app__hero">
        <div className="app__hero-content">
          <p className="app__tagline">Hallucination-proof research</p>
          <h1 className="app__title">Literature Review Assistant</h1>
          <p className="app__subtitle">
            Every claim is cited. Every quote is traceable. No hallucinations.
          </p>
        </div>
      </header>

      {/* Main content area */}
      <main className="app__main">
        <div className="app__container">
          {/* Main content - full width now */}
          <div className="app__content">
            {renderMainContent()}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="app__footer">
        <p>Built with transparency in mind.</p>
      </footer>
    </div>
  );
}

export default App;
