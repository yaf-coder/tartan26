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
import type { AppState, LoadingStep, Source, UploadedFile } from './types';

// Components
import {
  ChatInput,
  UploadDropzone,
  ProgressStepper,
  LiteratureReview,
} from './components';

// API
import { submitResearchStream, getPaperDownloadUrl } from './api';

// Styles
import './App.css';

// -----------------------------------------------------------------------------
// CONSTANTS
// -----------------------------------------------------------------------------

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

  /** Results: sources and summary from the API */
  const [sources, setSources] = useState<Source[]>([]);
  const [summary, setSummary] = useState('');

  /** Error message when request fails */
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /** Names of source PDF files from the last research (for popup + download) */
  const [sourceFiles, setSourceFiles] = useState<string[]>([]);

  /** Whether to show the source files popup */
  const [showSourceFilesPopup, setShowSourceFilesPopup] = useState(false);

  // ---------------------------------------------------------------------------
  // HANDLERS
  // ---------------------------------------------------------------------------

  /**
   * Handle query submission: call API with query; optional PDFs are sent as sources.
   * A question alone starts research (backend finds papers); any uploaded files are used as sources.
   */
  const handleSubmit = useCallback(async (submittedQuery: string) => {
    setQuery(submittedQuery);
    setErrorMessage(null);

    const pdfFiles = files
      .filter((f): f is UploadedFile & { file: File } => !!f.file && f.name.toLowerCase().endsWith('.pdf'))
      .map((f) => f.file);

    setAppState('loading');
    setCurrentStep('finding-sources');

    try {
      await submitResearchStream(submittedQuery.trim(), pdfFiles, {
        onStep(step) {
          setCurrentStep(step);
        },
        onResult(result) {
          setSources(result.sources);
          setSummary(result.summary);
          setSourceFiles(result.source_files ?? []);
          setAppState('results');
          if ((result.source_files?.length ?? 0) > 0) {
            setShowSourceFilesPopup(true);
          }
        },
        onError(message) {
          setErrorMessage(message);
          setAppState('error');
        },
      });
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Research request failed.');
      setAppState('error');
    }
  }, [files]);

  /**
   * Reset to idle state (start over)
   */
  const handleReset = useCallback(() => {
    setAppState('idle');
    setQuery('');
    setFiles([]);
    setSources([]);
    setSummary('');
    setSourceFiles([]);
    setShowSourceFilesPopup(false);
    setErrorMessage(null);
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
            {/* Trust badges */}
            <div className="app__trust-badges">
              <span className="app__trust-badge">Every claim is cited</span>
              <span className="app__trust-separator">•</span>
              <span className="app__trust-badge">Every quote is traceable</span>
              <span className="app__trust-separator">•</span>
              <span className="app__trust-badge">Every conclusion is verifiable</span>
            </div>

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

            <LiteratureReview sources={sources} summary={summary} />

            {/* Popup: source PDF files (names + download links) */}
            {showSourceFilesPopup && sourceFiles.length > 0 && (
              <div className="app__source-files-overlay" onClick={() => setShowSourceFilesPopup(false)}>
                <div className="app__source-files-popup" onClick={(e) => e.stopPropagation()}>
                  <div className="app__source-files-header">
                    <h3>Source files ({sourceFiles.length})</h3>
                    <button
                      type="button"
                      className="app__source-files-close"
                      onClick={() => setShowSourceFilesPopup(false)}
                      aria-label="Close"
                    >
                      ×
                    </button>
                  </div>
                  <ul className="app__source-files-list">
                    {sourceFiles.map((name) => (
                      <li key={name} className="app__source-files-item">
                        <span className="app__source-files-name">{name}</span>
                        <a
                          href={getPaperDownloadUrl(name)}
                          target="_blank"
                          rel="noopener noreferrer"
                          download={name}
                          className="app__source-files-download"
                        >
                          Download
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        );

      case 'error':
        return (
          <div className="app__error-section">
            <div className="app__error-message">
              <h3>Something went wrong</h3>
              <p>{errorMessage ?? "We couldn't complete your research. Please try again."}</p>
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
          <h1 className="app__title">Veritas</h1>
          <p className="app__subtitle-brand">the truth agent</p>
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
