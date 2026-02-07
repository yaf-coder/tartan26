/**
 * =============================================================================
 * LITERATURE REVIEW COMPONENT
 * =============================================================================
 * 
 * Displays the complete literature review results with:
 * - Executive summary section
 * - Comprehensive literature review document (NEW!)
 * - Scrollable list of SourceCards
 * 
 * This is the main results component shown after analysis is complete.
 * 
 * PROPS:
 * - sources: array of Source objects from mockData
 * - summary: the executive summary paragraph
 * - literatureReview: comprehensive literature review document (markdown)
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
    /** Executive summary paragraph */
    summary: string;
    /** Comprehensive literature review markdown document */
    literatureReview?: string;
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function LiteratureReview({ sources, summary, literatureReview }: LiteratureReviewProps) {
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

            {/* Executive Summary section */}
            {summary && (
                <section className="literature-review__summary">
                    <h3 className="literature-review__section-title">Executive Summary</h3>
                    <p className="literature-review__summary-text">{summary}</p>
                </section>
            )}

            {/* Comprehensive Literature Review Document (NEW!) */}
            {literatureReview && (
                <section className="literature-review__comprehensive">
                    <h3 className="literature-review__section-title">Comprehensive Research Report</h3>
                    <div
                        className="literature-review__markdown"
                        dangerouslySetInnerHTML={{
                            __html: literatureReview
                                .replace(/^# /gm, '<h2>')
                                .replace(/\n## /g, '</h2><h3>')
                                .replace(/\n### /g, '</h3><h4>')
                                .replace(/\n/g, '<br/>')
                                .replace(/<h2>/g, '<h2 class="lit-h2">')
                                .replace(/<h3>/g, '<h3 class="lit-h3">')
                                .replace(/<h4>/g, '<h4 class="lit-h4">')
                                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                                .replace(/\[([^\]]+)\]/g, '<cite>[$1]</cite>')
                        }}
                    />
                </section>
            )}

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
