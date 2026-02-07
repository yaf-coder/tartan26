/**
 * =============================================================================
 * VALIDATION SIDEBAR COMPONENT
 * =============================================================================
 * 
 * The right sidebar showing:
 * - Product branding and trust messaging
 * - Validation metrics (sources, quotes, citations)
 * - Verification progress bar
 * - Trust badges
 * 
 * This component reinforces the "no hallucinations" messaging.
 * 
 * PROPS:
 * - status: ValidationStatus object with metrics
 * - isLoading: whether analysis is in progress
 * =============================================================================
 */

import type { ValidationStatus } from '../types';
import './ValidationSidebar.css';

// -----------------------------------------------------------------------------
// TYPE DEFINITIONS
// -----------------------------------------------------------------------------

interface ValidationSidebarProps {
    /** Validation metrics to display */
    status: ValidationStatus;
    /** Is the analysis currently in progress? */
    isLoading: boolean;
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function ValidationSidebar({ status, isLoading }: ValidationSidebarProps) {
    return (
        <aside className="validation-sidebar">
            {/* Trust section with badges */}
            <div className="validation-sidebar__trust">
                <h3 className="validation-sidebar__trust-title">
                    Our Promise
                </h3>

                <div className="validation-sidebar__badges">
                    <div className="validation-sidebar__badge">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            <polyline points="22 4 12 14.01 9 11.01" />
                        </svg>
                        Zero Hallucinations
                    </div>

                    <div className="validation-sidebar__badge">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        Only Cited Claims
                    </div>

                    <div className="validation-sidebar__badge">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                        </svg>
                        Direct Quotes
                    </div>

                    <div className="validation-sidebar__badge">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="12 6 12 12 16 14" />
                        </svg>
                        Fully Traceable
                    </div>
                </div>
            </div>

            {/* Verification meter */}
            <div className="validation-sidebar__meter">
                <div className="validation-sidebar__meter-header">
                    <span className="validation-sidebar__meter-label">
                        Source Coverage
                    </span>
                    <span className="validation-sidebar__meter-value">
                        {isLoading ? '...' : `${status.coveragePercent}%`}
                    </span>
                </div>
                <div className="validation-sidebar__meter-bar">
                    <div
                        className={`validation-sidebar__meter-fill ${isLoading ? 'validation-sidebar__meter-fill--loading' : ''}`}
                        style={{ width: isLoading ? '60%' : `${status.coveragePercent}%` }}
                    />
                </div>
            </div>

            {/* Metrics grid */}
            <div className="validation-sidebar__metrics">
                <div className="validation-sidebar__metric">
                    <span className="validation-sidebar__metric-value">
                        {isLoading ? (
                            <span className="validation-sidebar__metric-loading">...</span>
                        ) : (
                            status.sourcesFound
                        )}
                    </span>
                    <span className="validation-sidebar__metric-label">
                        Sources Found
                    </span>
                </div>

                <div className="validation-sidebar__metric">
                    <span className="validation-sidebar__metric-value">
                        {isLoading ? (
                            <span className="validation-sidebar__metric-loading">...</span>
                        ) : (
                            status.quotesExtracted
                        )}
                    </span>
                    <span className="validation-sidebar__metric-label">
                        Quotes Extracted
                    </span>
                </div>

                <div className="validation-sidebar__metric">
                    <span className="validation-sidebar__metric-value">
                        {isLoading ? (
                            <span className="validation-sidebar__metric-loading">...</span>
                        ) : (
                            status.citationsValidated
                        )}
                    </span>
                    <span className="validation-sidebar__metric-label">
                        Citations Validated
                    </span>
                </div>
            </div>

            {/* Validation status indicator */}
            <div className={`validation-sidebar__status ${isLoading ? 'validation-sidebar__status--loading' : 'validation-sidebar__status--complete'}`}>
                {isLoading ? (
                    <>
                        <div className="validation-sidebar__status-spinner" />
                        Analyzing...
                    </>
                ) : status.sourcesFound > 0 ? (
                    <>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            <polyline points="22 4 12 14.01 9 11.01" />
                        </svg>
                        All Claims Validated
                    </>
                ) : (
                    <>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                        </svg>
                        Ready to Analyze
                    </>
                )}
            </div>
        </aside>
    );
}
