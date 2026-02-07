/**
 * =============================================================================
 * PROGRESS STEPPER COMPONENT
 * =============================================================================
 * 
 * Shows the 4-step loading process with animations.
 * 
 * STEPS:
 * 1. Finding sources...
 * 2. Extracting quotes...
 * 3. Cross-checking claims...
 * 4. Compiling literature review...
 * 
 * Each step has three states:
 * - Pending: gray, waiting to start
 * - Active: blue, currently processing (with pulse animation)
 * - Complete: green, finished with checkmark
 * 
 * PROPS:
 * - currentStep: which step is currently active
 * =============================================================================
 */

import type { LoadingStep, ThinkingLog } from '../types';
import './ProgressStepper.css';

// -----------------------------------------------------------------------------
// CONSTANTS
// -----------------------------------------------------------------------------

/** Define the steps in order with their labels */
const STEPS: { key: LoadingStep; label: string }[] = [
    { key: 'finding-sources', label: 'Finding sources' },
    { key: 'extracting-quotes', label: 'Extracting quotes' },
    { key: 'cross-checking', label: 'Cross-checking claims' },
    { key: 'compiling', label: 'Compiling review' },
];

// -----------------------------------------------------------------------------
// TYPE DEFINITIONS
// -----------------------------------------------------------------------------

interface ProgressStepperProps {
    /** The currently active step */
    currentStep: LoadingStep;
    /** Real-time thinking logs from the backend */
    logs: ThinkingLog[];
}

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------------------------

/**
 * Get the index of a step (0-3)
 */
function getStepIndex(step: LoadingStep): number {
    return STEPS.findIndex((s) => s.key === step);
}

/**
 * Determine the status of a step relative to the current step
 */
function getStepStatus(
    stepKey: LoadingStep,
    currentStep: LoadingStep
): 'pending' | 'active' | 'complete' {
    const stepIndex = getStepIndex(stepKey);
    const currentIndex = getStepIndex(currentStep);

    if (stepIndex < currentIndex) return 'complete';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function ProgressStepper({ currentStep, logs }: ProgressStepperProps) {
    return (
        <div className="progress-stepper" role="status" aria-live="polite">
            {/* Header */}
            <div className="progress-stepper__header">
                <div className="progress-stepper__spinner" />
                <span className="progress-stepper__title">Analyzing your query...</span>
            </div>

            {/* Steps list */}
            <ol className="progress-stepper__steps">
                {STEPS.map((step, index) => {
                    const status = getStepStatus(step.key, currentStep);

                    return (
                        <li
                            key={step.key}
                            className={`progress-stepper__step progress-stepper__step--${status}`}
                        >
                            {/* Step indicator (number or checkmark) */}
                            <div className="progress-stepper__indicator">
                                {status === 'complete' ? (
                                    // Checkmark icon for completed steps
                                    <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2.5"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    >
                                        <polyline points="20 6 9 17 4 12" />
                                    </svg>
                                ) : (
                                    // Step number for pending/active steps
                                    <span>{index + 1}</span>
                                )}
                            </div>

                            {/* Step label */}
                            <div className="progress-stepper__content">
                                <span className="progress-stepper__label">{step.label}</span>

                                {/* Thinking logs - shown ONLY for the active step to avoid clutter */}
                                {status === 'active' && logs && logs.some(l => l.step === step.key) && (
                                    <div className="progress-stepper__logs">
                                        {logs
                                            .filter(l => l.step === step.key)
                                            .slice(-3) // Show last 3 for brevity
                                            .map((log, i) => (
                                                <div key={i} className="progress-stepper__log">
                                                    <span className="progress-stepper__log-bullet">›</span>
                                                    <span className="progress-stepper__log-text">{log.message}</span>
                                                </div>
                                            ))
                                        }
                                    </div>
                                )}
                            </div>

                            {/* Active step has a pulsing dot */}
                            {status === 'active' && (
                                <span className="progress-stepper__pulse" />
                            )}
                        </li>
                    );
                })}
            </ol>

            {/* Progress bar */}
            <div className="progress-stepper__bar">
                <div
                    className="progress-stepper__bar-fill"
                    style={{ width: `${((getStepIndex(currentStep) + 1) / STEPS.length) * 100}%` }}
                />
            </div>
        </div>
    );
}
