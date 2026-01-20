
import React, { useState } from 'react';
import { ExternalLink, Star, X, Loader2 } from 'lucide-react';

interface PropertyProps {
    id: string;
    title: string;
    url: string;
    price: string;
    location: string;
    description: string;
    score: number;
    bed_count: number;
    acreage: number;
    nearest_airport: string;
    drive_time_minutes: number;
    ai_summary: string;
    image_url: string | null;
    status?: string;
    funnel_stage?: string;
    is_new?: boolean;
    verification_reason?: string;
    source_type?: string;
    onStar?: (id: string) => void;
    onDismiss?: (id: string, reason: string) => void;
    isUpdating?: boolean;
}

const DISMISS_REASONS = [
    { value: 'already_sold', label: 'Already Sold' },
    { value: 'not_relevant', label: 'Not Relevant' },
    { value: 'wrong_type', label: 'Wrong Property Type' },
    { value: 'too_expensive', label: 'Too Expensive' },
    { value: 'too_small', label: 'Too Small' },
    { value: 'bad_location', label: 'Bad Location' },
    { value: 'duplicate', label: 'Duplicate' },
];

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
    listing: { label: 'Listing', color: 'bg-green-100 text-green-700' },
    auction: { label: 'Auction', color: 'bg-orange-100 text-orange-700' },
    news: { label: 'News', color: 'bg-blue-100 text-blue-700' },
    foreclosure: { label: 'Foreclosure', color: 'bg-red-100 text-red-700' },
};

const PropertyCard: React.FC<PropertyProps> = (props) => {
    const [showDismissMenu, setShowDismissMenu] = useState(false);
    const isStarred = props.status === 'Starred';

    // Only show image if it's a real listing image (not null/empty)
    const hasRealImage = props.image_url && props.image_url.trim() !== '';

    const sourceBadge = SOURCE_BADGES[props.source_type || 'news'] || SOURCE_BADGES.news;

    return (
        <div className={`group flex items-stretch bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden hover:shadow-md transition-all duration-200 ${props.is_new ? 'ring-2 ring-blue-500/30' : ''}`}>

            {/* Thumbnail - Fixed width column */}
            <div className="flex-shrink-0 w-20 bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center relative">
                {hasRealImage ? (
                    <img
                        src={props.image_url!}
                        alt={props.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                        }}
                    />
                ) : (
                    <span className="text-2xl text-zinc-300 dark:text-zinc-600">🏢</span>
                )}
                {/* New badge */}
                {props.is_new && (
                    <span className="absolute top-1 left-1 bg-blue-600 text-white text-[8px] px-1 rounded font-bold">
                        NEW
                    </span>
                )}
            </div>

            {/* Score - Fixed width column */}
            <div className="flex-shrink-0 w-12 flex items-center justify-center border-l border-zinc-100 dark:border-zinc-800">
                <div className="text-center">
                    <div className="text-lg font-bold text-zinc-700 dark:text-zinc-300">{props.score}</div>
                    <div className="text-[10px] text-zinc-400 uppercase">Score</div>
                </div>
            </div>

            {/* Title & Location - Flexible width */}
            <div className="flex-1 min-w-0 px-3 py-2 border-l border-zinc-100 dark:border-zinc-800">
                <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate group-hover:text-blue-600 transition-colors">
                    <a href={props.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                        {props.title}
                        <ExternalLink size={10} className="flex-shrink-0 opacity-0 group-hover:opacity-50" />
                    </a>
                </h3>
                <div className="text-xs text-zinc-500 dark:text-zinc-400 truncate mt-0.5">
                    {props.location}
                </div>
                {/* Status badges */}
                <div className="flex gap-1 mt-1">
                    {isStarred && <span className="bg-yellow-100 text-yellow-700 text-[10px] px-1 rounded">★ Starred</span>}
                </div>
            </div>

            {/* Stats Columns - Fixed widths for alignment */}
            <div className="flex-shrink-0 w-16 flex flex-col items-center justify-center border-l border-zinc-100 dark:border-zinc-800 py-2">
                <div className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                    {props.bed_count > 0 ? props.bed_count : '—'}
                </div>
                <div className="text-[10px] text-zinc-400 uppercase">Beds</div>
            </div>

            <div className="flex-shrink-0 w-16 flex flex-col items-center justify-center border-l border-zinc-100 dark:border-zinc-800 py-2">
                <div className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                    {props.acreage > 0 ? props.acreage : '—'}
                </div>
                <div className="text-[10px] text-zinc-400 uppercase">Acres</div>
            </div>

            <div className="flex-shrink-0 w-20 flex flex-col items-center justify-center border-l border-zinc-100 dark:border-zinc-800 py-2">
                <div className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 truncate max-w-full px-1">
                    {props.price && props.price !== 'Price TBD' ? props.price : '—'}
                </div>
                <div className="text-[10px] text-zinc-400 uppercase">Price</div>
            </div>

            {/* Source Type */}
            <div className="flex-shrink-0 w-14 flex flex-col items-center justify-center border-l border-zinc-100 dark:border-zinc-800 py-2">
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${sourceBadge.color}`}>
                    {sourceBadge.label}
                </span>
            </div>

            {/* Action Buttons */}
            <div className="flex-shrink-0 flex items-center border-l border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 relative">
                {props.isUpdating ? (
                    <div className="px-3">
                        <Loader2 size={16} className="animate-spin text-zinc-400" />
                    </div>
                ) : (
                    <>
                        <button
                            onClick={() => props.onStar?.(props.id)}
                            className={`p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors ${isStarred ? 'text-yellow-500' : 'text-zinc-400 hover:text-yellow-500'}`}
                            title={isStarred ? 'Remove star' : 'Star'}
                        >
                            <Star size={16} fill={isStarred ? 'currentColor' : 'none'} />
                        </button>
                        <div className="relative">
                            <button
                                onClick={() => setShowDismissMenu(!showDismissMenu)}
                                className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-400 hover:text-red-500"
                                title="Dismiss"
                            >
                                <X size={16} />
                            </button>
                            {/* Dismiss dropdown */}
                            {showDismissMenu && (
                                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg shadow-lg py-1 z-20 min-w-[150px]">
                                    {DISMISS_REASONS.map(reason => (
                                        <button
                                            key={reason.value}
                                            onClick={() => {
                                                props.onDismiss?.(props.id, reason.value);
                                                setShowDismissMenu(false);
                                            }}
                                            className="w-full text-left px-3 py-1.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
                                        >
                                            {reason.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>

        </div>
    );
};

export default PropertyCard;

