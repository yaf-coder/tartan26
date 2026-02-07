/**
 * =============================================================================
 * LITERATURE REVIEW COMPONENT
 * =============================================================================
 * 
 * Displays the complete literature review results with:
 * - A summary section at the top
 * - Scrollable list of SourceCards (20 sources)
 * 
 * This is the main results component shown after analysis is complete.
 * 
 * PROPS:
 * - sources: array of Source objects from mockData
 * - summary: the summary text for the review
 * =============================================================================
 */

import type { Source } from '../types';
import { SourceCard } from './SourceCard';
import './LiteratureReview.css';

// -----------------------------------------------------------------------------
// TYPE DEFINITIONS
// -----------------------------------------------------------------------------

interface LiteratureReviewProps {
    /** Array of sources to display */
    sources: Source[];
    /** Summary paragraph for the review */
    summary: string;
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function LiteratureReview({ sources, summary }: LiteratureReviewProps) {
    // Calculate some stats for the header
    const totalQuotes = sources.reduce((acc, s) => acc + s.quotes.length, 0);
    const totalFindings = sources.reduce((acc, s) => acc + s.keyFindings.length, 0);

    return (
        <div className="literature-review">
            {/* Header */}
            <header className="literature-review__header">
                <h2 className="literature-review__title">Literature Review</h2>

                {/* Stats badges */}
                <div className="literature-review__stats">
                    <span className="literature-review__stat">
                        <strong>{sources.length}</strong> sources
                    </span>
                    <span className="literature-review__stat">
                        <strong>{totalQuotes}</strong> quotes
                    </span>
                    <span className="literature-review__stat">
                        <strong>{totalFindings}</strong> findings
                    </span>
                </div>
            </header>

            {/* Summary section */}
            <section className="literature-review__summary">
                <h3 className="literature-review__section-title">Executive Summary</h3>
                <p className="literature-review__summary-text">{summary}</p>
            </section>

            {/* Sources section */}
            <section className="literature-review__sources">
                <h3 className="literature-review__section-title">
                    Sources ({sources.length})
                </h3>

                {/* Scrollable list of source cards */}
                <div className="literature-review__source-list">
                    {sources.map((source) => (
                        <SourceCard key={source.id} source={source} />
                    ))}
                </div>
            </section>
        </div>
    );
}
