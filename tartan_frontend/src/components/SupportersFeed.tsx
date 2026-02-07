/**
 * =============================================================================
 * SUPPORTERS FEED COMPONENT
 * =============================================================================
 * 
 * A social proof strip showing:
 * - Total raised amount and supporter count
 * - Animated live-style feed of supporter events
 * 
 * The animation cycles through mock supporter events to create
 * a sense of activity and social validation.
 * 
 * This component is self-contained with its own animation state.
 * =============================================================================
 */

import { useState, useEffect } from 'react';
import './SupportersFeed.css';

// -----------------------------------------------------------------------------
// MOCK SUPPORTER DATA
// -----------------------------------------------------------------------------

/** Anonymized supporter names */
const SUPPORTER_NAMES = [
    'Alex M.',
    'Jordan K.',
    'Sam T.',
    'Riley P.',
    'Casey W.',
    'Morgan L.',
    'Taylor H.',
    'Drew N.',
    'Jamie S.',
    'Quinn R.',
];

/** Random support amounts */
const AMOUNTS = [25, 50, 75, 100, 150, 200, 250, 500];

/** Random cities */
const CITIES = [
    'San Francisco',
    'New York',
    'Austin',
    'Seattle',
    'Boston',
    'Denver',
    'Chicago',
    'Portland',
    'Miami',
    'Atlanta',
];

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------------------------

/**
 * Generate a random supporter event
 */
function generateEvent(): { name: string; amount: number; city: string; time: string } {
    const name = SUPPORTER_NAMES[Math.floor(Math.random() * SUPPORTER_NAMES.length)];
    const amount = AMOUNTS[Math.floor(Math.random() * AMOUNTS.length)];
    const city = CITIES[Math.floor(Math.random() * CITIES.length)];
    const minutes = Math.floor(Math.random() * 30) + 1;
    const time = `${minutes} min ago`;

    return { name, amount, city, time };
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function SupportersFeed() {
    // State: current event to display
    const [currentEvent, setCurrentEvent] = useState(generateEvent);

    // State: is the event visible (for fade animation)
    const [isVisible, setIsVisible] = useState(true);

    // Effect: cycle through events every 4 seconds
    useEffect(() => {
        const interval = setInterval(() => {
            // Fade out
            setIsVisible(false);

            // After fade out, change event and fade in
            setTimeout(() => {
                setCurrentEvent(generateEvent());
                setIsVisible(true);
            }, 300); // Match this to CSS transition duration
        }, 4000);

        // Cleanup on unmount
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="supporters-feed">
            {/* Total raised section */}
            <div className="supporters-feed__total">
                <span className="supporters-feed__amount">$76,455</span>
                <span className="supporters-feed__label">
                    raised from <strong>3,817</strong> early supporters
                </span>
            </div>

            {/* Separator */}
            <div className="supporters-feed__separator" />

            {/* Live event feed */}
            <div className={`supporters-feed__event ${isVisible ? 'supporters-feed__event--visible' : ''}`}>
                {/* Live indicator dot */}
                <span className="supporters-feed__live-dot" />

                <span className="supporters-feed__event-text">
                    <strong>{currentEvent.name}</strong> from {currentEvent.city} contributed ${currentEvent.amount}
                </span>

                <span className="supporters-feed__event-time">
                    {currentEvent.time}
                </span>
            </div>
        </div>
    );
}
