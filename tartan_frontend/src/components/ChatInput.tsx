/**
 * =============================================================================
 * CHAT INPUT COMPONENT
 * =============================================================================
 * 
 * A textarea input for entering research queries, with a submit button.
 * 
 * FEATURES:
 * - Multiline textarea that grows with content
 * - Submit button that's disabled when empty
 * - Handles Enter key (Shift+Enter for new line)
 * - Accessible with proper labels
 * 
 * PROPS:
 * - onSubmit: function called when user submits a query
 * - disabled: boolean to disable input during loading
 * - placeholder: optional custom placeholder text
 * =============================================================================
 */

import { useState, useRef } from 'react';
import type { KeyboardEvent, ChangeEvent } from 'react';
import './ChatInput.css';

// -----------------------------------------------------------------------------
// TYPE DEFINITIONS
// -----------------------------------------------------------------------------

interface ChatInputProps {
    /** Called when user submits a query */
    onSubmit: (query: string) => void;
    /** Disable input (e.g., during loading) */
    disabled?: boolean;
    /** Custom placeholder text */
    placeholder?: string;
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function ChatInput({
    onSubmit,
    disabled = false,
    placeholder = "Enter your research query..."
}: ChatInputProps) {
    // State: the current text in the textarea
    const [query, setQuery] = useState('');

    // Ref: used to access the textarea element directly
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // ---------------------------------------------------------------------------
    // HANDLERS
    // ---------------------------------------------------------------------------

    /**
     * Handle text changes in the textarea
     */
    const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
        setQuery(e.target.value);

        // Auto-resize textarea to fit content
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    };

    /**
     * Handle form submission
     */
    const handleSubmit = () => {
        // Don't submit if empty or disabled
        const trimmedQuery = query.trim();
        if (!trimmedQuery || disabled) return;

        // Call the parent's onSubmit function
        onSubmit(trimmedQuery);

        // Clear the input after submission
        setQuery('');

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    /**
     * Handle keyboard shortcuts
     * - Enter: Submit (unless Shift is held)
     * - Shift+Enter: New line
     */
    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // Prevent new line
            handleSubmit();
        }
    };

    // ---------------------------------------------------------------------------
    // RENDER
    // ---------------------------------------------------------------------------

    // Check if the submit button should be disabled
    const isSubmitDisabled = disabled || !query.trim();

    return (
        <div className="chat-input">
            {/* Label for accessibility (visually hidden) */}
            <label htmlFor="research-query" className="chat-input__label">
                Research Query
            </label>

            {/* Main textarea */}
            <textarea
                ref={textareaRef}
                id="research-query"
                className="chat-input__textarea"
                value={query}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                rows={3}
                aria-describedby="chat-input-hint"
            />

            {/* Bottom bar with hint and submit button */}
            <div className="chat-input__footer">
                <span id="chat-input-hint" className="chat-input__hint">
                    Press Enter to submit, Shift+Enter for new line
                </span>

                <button
                    type="button"
                    className="chat-input__submit"
                    onClick={handleSubmit}
                    disabled={isSubmitDisabled}
                    aria-label="Submit research query"
                >
                    {/* Arrow icon */}
                    <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <line x1="22" y1="2" x2="11" y2="13" />
                        <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                    <span>Research</span>
                </button>
            </div>
        </div>
    );
}
