-- Supabase SQL Schema for Edge City Finder
-- Run this in the Supabase SQL editor to create the properties table

-- Enable UUID extension if not already enabled
create extension if not exists "uuid-ossp";

-- Create properties table
create table if not exists properties (
    id uuid primary key default uuid_generate_v4(),
    title text not null,
    url text not null unique,
    price text,
    location text,
    description text,
    status text default 'New' check (status in ('New', 'Starred', 'Reviewed', 'Contacted', 'Passed', 'Archived')),
    score integer default 0,
    
    -- Vital Stats
    acreage numeric,
    bed_count integer,
    year_built integer,
    
    -- Logistics
    nearest_airport text,
    drive_time_minutes integer,
    
    -- AI
    ai_summary text,
    image_url text,
    
    -- Funnel Tracking
    funnel_stage text default 'discovered' check (funnel_stage in ('discovered', 'qualified', 'interesting', 'contacted', 'dismissed')),
    is_new boolean default true,
    
    -- Verification Metadata
    verification_result text,      -- 'available', 'sold', 'not_listing', 'invalid_url', etc.
    verification_reason text,      -- Human-readable explanation
    last_verified_at timestamp with time zone,
    source_type text,              -- 'listing', 'news', 'auction', 'foreclosure'
    
    -- Discovery Metadata
    discovered_via text,           -- 'exa_loopnet', 'tavily_news', 'manual', etc.
    search_query text,             -- The query that found this
    
    -- Feedback Learning
    dismissed_reason text,         -- 'already_sold', 'not_relevant', 'wrong_type', etc.
    dismissed_pattern text,        -- Extracted pattern for future filtering
    
    -- Timestamps
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Create index on status for filtering
create index if not exists idx_properties_status on properties(status);

-- Create index on funnel_stage for filtering
create index if not exists idx_properties_funnel_stage on properties(funnel_stage);

-- Create index on created_at for sorting
create index if not exists idx_properties_created_at on properties(created_at desc);

-- Create trigger to auto-update updated_at
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists update_properties_updated_at on properties;
create trigger update_properties_updated_at
    before update on properties
    for each row
    execute function update_updated_at_column();

-- Row Level Security (RLS) - Optional, enable if using auth
-- alter table properties enable row level security;

-- Policy examples (uncomment if using RLS):
-- create policy "Enable read access for all users" on properties for select using (true);
-- create policy "Enable insert for authenticated users" on properties for insert with check (auth.role() = 'authenticated');
-- create policy "Enable update for authenticated users" on properties for update using (auth.role() = 'authenticated');
