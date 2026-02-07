/**
 * =============================================================================
 * SOURCE CARD COMPONENT
 * =============================================================================
 * 
 * Displays a single research source with its metadata, quotes, and findings.
 * 
 * STRUCTURE:
 * - Header: Source number, title, publisher, date
 * - Link: Placeholder URL to the source
 * - Quotes: 1-3 direct quotes styled as blockquotes
 * - Key Findings: Bullet list with source reference chips
 * 
 * PROPS:
 * - source: the Source object from mockData
 * =============================================================================
 */

import type { Source } from '../types';
import './SourceCard.css';

// -----------------------------------------------------------------------------
// TYPE DEFINITIONS
// -----------------------------------------------------------------------------

interface SourceCardProps {
    /** The source data to display */
    source: Source;
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function SourceCard({ source }: SourceCardProps) {
    return (
        <article className="source-card">
            {/* Header with source number and metadata */}
            <header className="source-card__header">
                {/* Source number badge */}
                <span className="source-card__number">
                    Source {source.id}
                </span>

                {/* Verified badge */}
                <span className="source-card__verified">
                    <svg
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                    >
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
                    </svg>
                    Verified
                </span>
            </header>

            {/* Title */}
            <h3 className="source-card__title">{source.title}</h3>

            {/* Metadata row */}
            <div className="source-card__meta">
                <span className="source-card__publisher">{source.publisher}</span>
                <span className="source-card__separator">•</span>
                <span className="source-card__date">{source.date}</span>
            </div>

            {/* Source link */}
            <a
                href={source.url}
                className="source-card__link"
                target="_blank"
                rel="noopener noreferrer"
            >
                <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                >
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                View source
            </a>

            {/* Quotes section */}
            <div className="source-card__quotes">
                <h4 className="source-card__section-title">
                    Direct Quotes ({source.quotes.length})
                </h4>
                <div className="source-card__quote-list">
                    {source.quotes.map((quote) => (
                        <blockquote key={quote.id} className="source-card__quote">
                            {/* Quote reference chip */}
                            <span className="source-card__quote-ref">
                                Quote #{quote.id}
                            </span>
                            <p className="source-card__quote-text">"{quote.text}"</p>
                        </blockquote>
                    ))}
                </div>
            </div>

            {/* Key findings section */}
            <div className="source-card__findings">
                <h4 className="source-card__section-title">
                    Key Findings ({source.keyFindings.length})
                </h4>
                <ul className="source-card__findings-list">
                    {source.keyFindings.map((finding, index) => (
                        <li key={index} className="source-card__finding">
                            <span className="source-card__finding-text">{finding}</span>
                            {/* Source reference chip */}
                            <span className="source-card__finding-ref">
                                Source {source.id}
                            </span>
                        </li>
                    ))}
                </ul>
            </div>
        </article>
    );
}
