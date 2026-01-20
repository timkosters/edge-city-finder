-- Migration script for existing databases
-- Run this in Supabase SQL editor to add the new funnel columns

-- Funnel Tracking
ALTER TABLE properties ADD COLUMN IF NOT EXISTS funnel_stage text default 'discovered' 
    check (funnel_stage in ('discovered', 'qualified', 'interesting', 'contacted', 'dismissed'));
ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_new boolean default true;

-- Verification Metadata
ALTER TABLE properties ADD COLUMN IF NOT EXISTS verification_result text;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS verification_reason text;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS last_verified_at timestamp with time zone;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS source_type text;

-- Discovery Metadata
ALTER TABLE properties ADD COLUMN IF NOT EXISTS discovered_via text;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS search_query text;

-- Feedback Learning
ALTER TABLE properties ADD COLUMN IF NOT EXISTS dismissed_reason text;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS dismissed_pattern text;

-- Index for funnel stage filtering
CREATE INDEX IF NOT EXISTS idx_properties_funnel_stage ON properties(funnel_stage);

-- Set existing properties to 'qualified' since they were already in the system
UPDATE properties SET funnel_stage = 'qualified' WHERE funnel_stage = 'discovered';
