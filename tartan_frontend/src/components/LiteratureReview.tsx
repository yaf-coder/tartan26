/**
 * =============================================================================
 * LITERATURE REVIEW COMPONENT - POLISHED UI
 * =============================================================================
 */

import { useState } from 'react';
import type { Source } from '../types';
import { SourceCard } from './SourceCard';
import { generatePDF } from '../utils/pdfGenerator';
import './LiteratureReview.css';

interface LiteratureReviewProps {
    sources: Source[];
    summary: string;
    literatureReview?: string;
}

export function LiteratureReview({ sources, summary, literatureReview }: LiteratureReviewProps) {
    const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

    const totalQuotes = sources.reduce((acc, s) => acc + s.quotes.length, 0);
    const totalFindings = sources.reduce((acc, s) => acc + s.keyFindings.length, 0);

    const downloadSummary = async () => {
        setIsGeneratingPDF(true);
        try {
            await generatePDF({
                title: 'Executive Summary',
                content: summary,
                type: 'summary'
            });
        } finally {
            setIsGeneratingPDF(false);
        }
    };

    const downloadReport = async () => {
        if (!literatureReview) return;
        setIsGeneratingPDF(true);
        try {
            await generatePDF({
                title: 'Comprehensive Literature Review',
                content: literatureReview,
                sources: sources,
                type: 'full_report'
            });
        } finally {
            setIsGeneratingPDF(false);
        }
    };

    return (
        <div className="literature-review">
            {/* Header */}
            <header className="literature-review__header">
                <h2 className="literature-review__title">Literature Review</h2>

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

            {/* Research Report Download - MOVED TO TOP */}
            {literatureReview && (
                <section className="literature-review__report-download">
                    <button
                        onClick={downloadReport}
                        className="literature-review__report-btn"
                        disabled={isGeneratingPDF}
                        title="Download full research report as PDF"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        <div className="literature-review__report-text">
                            <span className="literature-review__report-title">Comprehensive Research Report</span>
                            <span className="literature-review__report-subtitle">Download formatted PDF</span>
                        </div>
                        <svg className="literature-review__report-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                    </button>
                </section>
            )}

            {/* Executive Summary */}
            {summary && (
                <section className="literature-review__summary">
                    <div className="literature-review__summary-header">
                        <h3 className="literature-review__section-title">Executive Summary</h3>
                        <button
                            onClick={downloadSummary}
                            className="literature-review__download-btn"
                            disabled={isGeneratingPDF}
                            title="Download summary as PDF"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="7 10 12 15 17 10" />
                                <line x1="12" y1="15" x2="12" y2="3" />
                            </svg>
                            PDF
                        </button>
                    </div>
                    <div className="literature-review__summary-text">{summary}</div>
                </section>
            )}

            {/* Sources section */}
            <section className="literature-review__sources">
                <h3 className="literature-review__section-title">
                    Sources ({sources.length})
                </h3>
                <p className="literature-review__sources-hint">
                    Click to expand
                </p>

                <div className="literature-review__source-list">
                    {sources.map((source) => (
                        <SourceCard key={source.id} source={source} />
                    ))}
                </div>
            </section>
        </div>
    );
}
