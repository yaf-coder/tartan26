/**
 * =============================================================================
 * TYPES.TS - Type Definitions for the Research Chatbot
 * =============================================================================
 * 
 * This file contains all TypeScript interfaces and types used throughout
 * the application. Having types in a single file makes it easy to understand
 * the data structures used in the app.
 * 
 * HOW TO USE:
 * Import types like: import { Source, Quote } from './types';
 * =============================================================================
 */

// -----------------------------------------------------------------------------
// QUOTE - A direct quote extracted from a research source
// -----------------------------------------------------------------------------
export interface Quote {
  /** Unique identifier for the quote (e.g., 1, 2, 3) */
  id: number;
  /** The actual quoted text from the source */
  text: string;
}

// -----------------------------------------------------------------------------
// SOURCE - A research source (paper, article, report, etc.)
// -----------------------------------------------------------------------------
export interface Source {
  /** Unique identifier for the source (1-20 in our mock data) */
  id: number;
  /** Title of the research paper/article */
  title: string;
  /** Publisher or journal name */
  publisher: string;
  /** Publication date (formatted as string, e.g., "March 2024") */
  date: string;
  /** URL link to the source (placeholder in mock data) */
  url: string;
  /** Array of direct quotes extracted from this source */
  quotes: Quote[];
  /** Key findings/takeaways from this source */
  keyFindings: string[];
}

// -----------------------------------------------------------------------------
// UPLOADED FILE - Represents a file the user has uploaded
// -----------------------------------------------------------------------------
export interface UploadedFile {
  /** Unique identifier (generated using crypto.randomUUID) */
  id: string;
  /** Original filename */
  name: string;
  /** File size in bytes */
  size: number;
  /** MIME type (e.g., 'application/pdf') */
  type: string;
  /** Actual File object for upload (set when file is added) */
  file?: File;
}

// -----------------------------------------------------------------------------
// VALIDATION STATUS - Shows the validation metrics in the sidebar
// -----------------------------------------------------------------------------
export interface ValidationStatus {
  /** Number of sources found and analyzed */
  sourcesFound: number;
  /** Number of direct quotes extracted */
  quotesExtracted: number;
  /** Number of citations validated */
  citationsValidated: number;
  /** Overall source coverage percentage (0-100) */
  coveragePercent: number;
}

// -----------------------------------------------------------------------------
// APP STATE - The four possible states of the application
// -----------------------------------------------------------------------------
export type AppState = 
  | 'idle'      // Initial state, waiting for user input
  | 'loading'   // Processing the research query
  | 'results'   // Showing the literature review results
  | 'error';    // Something went wrong

// -----------------------------------------------------------------------------
// LOADING STEP - The four steps shown during the loading process
// -----------------------------------------------------------------------------
export type LoadingStep = 
  | 'finding-sources'    // Step 1: Finding relevant sources
  | 'extracting-quotes'  // Step 2: Extracting direct quotes
  | 'cross-checking'     // Step 3: Cross-checking claims
  | 'compiling';         // Step 4: Compiling the literature review
 