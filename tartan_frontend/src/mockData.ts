/**
 * =============================================================================
 * MOCK DATA - Generates realistic mock data for 20 research sources
 * =============================================================================
 * 
 * This file creates fake/placeholder data to demonstrate the UI without
 * needing a real backend. All data is deterministic (same every time).
 * 
 * In a real app, this data would come from an API. For now, we use this
 * to build and test the frontend independently.
 * =============================================================================
 */

import type { Source, ValidationStatus } from './types';

// -----------------------------------------------------------------------------
// SAMPLE DATA ARRAYS
// These arrays provide variety for generating realistic-looking sources
// -----------------------------------------------------------------------------

/** Sample research paper titles - intentionally varied and academic-sounding */
const TITLES = [
    "Comprehensive Analysis of PFAS Contamination in Municipal Water Systems",
    "Long-term Health Outcomes Associated with PFAS Exposure",
    "Novel Filtration Technologies for PFAS Removal",
    "Environmental Persistence of Per- and Polyfluoroalkyl Substances",
    "Regulatory Frameworks for PFAS in Drinking Water: A Global Review",
    "Bioaccumulation Patterns of PFAS in Aquatic Ecosystems",
    "Cost-Benefit Analysis of PFAS Remediation Strategies",
    "Epidemiological Studies on PFAS and Thyroid Function",
    "Groundwater Contamination Pathways for PFAS Compounds",
    "Comparative Effectiveness of Activated Carbon for PFAS Removal",
    "PFAS Detection Methods: Advances in Analytical Chemistry",
    "Community Health Impacts Near PFAS Manufacturing Sites",
    "Risk Assessment Models for PFAS in Drinking Water",
    "Emerging PFAS Alternatives and Their Environmental Fate",
    "Source Tracking of PFAS Contamination in Watershed Systems",
    "Developmental Effects of Prenatal PFAS Exposure",
    "Agricultural Impacts of PFAS-Contaminated Irrigation Water",
    "PFAS Remediation: A Review of Current Best Practices",
    "Public Health Policy Responses to PFAS Contamination",
    "Economic Burden of PFAS-Related Health Conditions",
];

/** Sample publishers - mix of journals, institutions, and agencies */
const PUBLISHERS = [
    "Environmental Science & Technology",
    "Journal of Environmental Health",
    "Water Research",
    "EPA Office of Research",
    "Nature Environmental Science",
    "American Journal of Public Health",
    "Environmental Health Perspectives",
    "Science of the Total Environment",
    "World Health Organization",
    "National Institute of Environmental Health Sciences",
];

/** Sample direct quotes - these would come from the actual sources in a real app */
const QUOTE_TEMPLATES = [
    "Our analysis revealed that PFAS concentrations exceeded safe drinking water thresholds in {percent}% of tested samples.",
    "The correlation between PFAS exposure and adverse health outcomes was statistically significant (p < 0.{pValue}).",
    "Activated carbon filtration demonstrated {percent}% removal efficiency for long-chain PFAS compounds.",
    "Longitudinal data spanning {years} years indicates persistent bioaccumulation in affected populations.",
    "Regulatory action is urgently needed given the widespread nature of contamination.",
    "Cost estimates for comprehensive remediation range from ${cost} million to ${costHigh} million per affected site.",
    "Community health screenings revealed elevated PFAS blood levels in {percent}% of residents.",
    "The half-life of PFOS in human serum was estimated at {years} years.",
    "Water treatment facilities using conventional methods showed minimal PFAS removal.",
    "Emerging treatment technologies show promise but require further validation.",
];

/** Sample key findings - concise, actionable statements */
const FINDING_TEMPLATES = [
    "PFAS contamination is more widespread than previously estimated",
    "Current detection limits may underestimate true exposure levels",
    "Long-chain PFAS compounds show higher persistence and toxicity",
    "Activated carbon remains the most cost-effective treatment option",
    "Regulatory standards vary significantly across jurisdictions",
    "Children and pregnant women face elevated health risks",
    "Source reduction is more effective than end-of-pipe treatment",
    "Public awareness correlates with increased testing demand",
    "Multi-stakeholder approaches yield better remediation outcomes",
    "Continuous monitoring is essential for early detection",
];

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------------------------

/**
 * Generates a random-looking date between 2020 and 2024
 * Uses the source index to make it deterministic (same every time)
 */
function generateDate(index: number): string {
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    const month = months[index % 12];
    const year = 2020 + (index % 5); // Years 2020-2024
    return `${month} ${year}`;
}

/**
 * Generates a quote with some variation by replacing placeholders
 */
function generateQuote(templateIndex: number, quoteId: number): string {
    const template = QUOTE_TEMPLATES[templateIndex % QUOTE_TEMPLATES.length];
    return template
        .replace('{percent}', String(45 + (quoteId * 7) % 50))
        .replace('{pValue}', String(1 + (quoteId % 4)))
        .replace('{years}', String(3 + (quoteId % 8)))
        .replace('{cost}', String(2 + (quoteId % 10)))
        .replace('{costHigh}', String(15 + (quoteId % 20)));
}

// -----------------------------------------------------------------------------
// MAIN EXPORT: Generate 20 mock sources
// -----------------------------------------------------------------------------

/**
 * Creates an array of 20 mock research sources
 * Each source has:
 * - Unique ID (1-20)
 * - Title, publisher, date
 * - 1-3 direct quotes
 * - 2-4 key findings
 */
export function generateMockSources(): Source[] {
    const sources: Source[] = [];

    for (let i = 0; i < 20; i++) {
        // Determine how many quotes and findings for this source (varies 1-3 and 2-4)
        const numQuotes = 1 + (i % 3);  // 1, 2, or 3 quotes
        const numFindings = 2 + (i % 3); // 2, 3, or 4 findings

        // Generate quotes for this source
        const quotes = [];
        for (let q = 0; q < numQuotes; q++) {
            quotes.push({
                id: q + 1,
                text: generateQuote(i + q, q + 1),
            });
        }

        // Generate key findings for this source
        const keyFindings = [];
        for (let f = 0; f < numFindings; f++) {
            keyFindings.push(FINDING_TEMPLATES[(i + f) % FINDING_TEMPLATES.length]);
        }

        // Create the source object
        sources.push({
            id: i + 1,
            title: TITLES[i],
            publisher: PUBLISHERS[i % PUBLISHERS.length],
            date: generateDate(i),
            url: `https://research.example.com/paper/${i + 1}`,
            quotes,
            keyFindings,
        });
    }

    return sources;
}

/**
 * Generates a summary paragraph for the literature review
 * In a real app, this would be generated by the AI backend
 */
export function generateMockSummary(): string {
    return `Based on analysis of 20 peer-reviewed sources, this literature review examines the current state of PFAS contamination in water systems. The research indicates widespread contamination affecting millions of people globally, with significant health implications including thyroid dysfunction, immune system effects, and developmental impacts. Current remediation strategies show varying effectiveness, with activated carbon filtration emerging as the most cost-effective solution for municipal water systems. Regulatory frameworks are evolving rapidly, though significant gaps remain in enforcement and monitoring. This review synthesizes findings from environmental studies, epidemiological research, and policy analyses spanning 2020-2024.`;
}

/**
 * Creates mock validation status data for the sidebar
 * These numbers represent the "validation" metrics shown in the UI
 */
export function generateMockValidationStatus(): ValidationStatus {
    return {
        sourcesFound: 20,
        quotesExtracted: 42,      // Sum of all quotes across sources
        citationsValidated: 20,   // All sources validated
        coveragePercent: 94,      // High coverage score
    };
}
