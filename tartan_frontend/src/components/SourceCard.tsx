/**
 * =============================================================================
 * SOURCE CARD - CLEAN MINIMAL DESIGN
 * =============================================================================
 */

import { useState } from 'react';
import type { Source } from '../types';
import './SourceCard.css';

interface SourceCardProps {
    source: Source;
}

export function SourceCard({ source }: SourceCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <article className={`source-card ${isExpanded ? 'source-card--expanded' : ''}`}>
            <button
                className="source-card__toggle"
                onClick={() => setIsExpanded(!isExpanded)}
                aria-expanded={isExpanded}
            >
                {/* Header */}
                <header className="source-card__header">
                    <span className="source-card__number">#{source.id}</span>
                    <h3 className="source-card__title">{source.title}</h3>
                    <svg
                        className="source-card__expand-icon"
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                    >
                        <polyline points={isExpanded ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
                    </svg>
                </header>

                {/* Metadata */}
                <div className="source-card__meta">
                    <span className="source-card__publisher">{source.publisher}</span>
                    {source.date && (
                        <>
                            <span className="source-card__separator">•</span>
                            <span className="source-card__date">{source.date}</span>
                        </>
                    )}
                    <span className="source-card__separator">•</span>
                    <span className="source-card__verified">✓ Verified</span>
                </div>
            </button>

            {/* Expandable content */}
            {isExpanded && (
                <div className="source-card__content">
                    {source.url && (
                        <a
                            href={source.url}
                            className="source-card__link"
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                        >
                            View Source →
                        </a>
                    )}

                    {/* Quotes */}
                    {source.quotes.length > 0 && (
                        <div className="source-card__quotes">
                            <h4 className="source-card__section-title">
                                Quotes ({source.quotes.length})
                            </h4>
                            <div className="source-card__quote-list">
                                {source.quotes.map((quote) => (
                                    <blockquote key={quote.id} className="source-card__quote">
                                        "{quote.text}"
                                    </blockquote>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Key findings */}
                    {source.keyFindings.length > 0 && (
                        <div className="source-card__findings">
                            <h4 className="source-card__section-title">
                                Key Findings ({source.keyFindings.length})
                            </h4>
                            <ul className="source-card__findings-list">
                                {source.keyFindings.map((finding, index) => (
                                    <li key={index} className="source-card__finding">
                                        {finding}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </article>
    );
}
