'use client';
import { useState, useEffect } from 'react';
import PropertyCard from '@/components/PropertyCard';
import { Search, Loader2, RefreshCw, Database, DatabaseZap, Sparkles, Newspaper } from 'lucide-react';

// Type matching the backend Property model
interface Property {
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
  image_url: string;
  status: string;
  funnel_stage: string;
  is_new: boolean;
  verification_reason: string;
  source_type: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type TabType = 'qualified' | 'interesting';

export default function Home() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [dbConnected, setDbConnected] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('qualified');
  const [customQuery, setCustomQuery] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);

  // Load properties based on active tab
  const loadProperties = async (tab: TabType = activeTab) => {
    try {
      const endpoint = tab === 'qualified'
        ? `${API_BASE_URL}/api/properties/qualified`
        : `${API_BASE_URL}/api/properties/interesting`;

      const response = await fetch(endpoint);
      if (!response.ok) throw new Error('Failed to fetch properties');

      const data = await response.json();

      if (data.properties) {
        const props = data.properties.map((prop: Partial<Property>, index: number) => ({
          id: prop.id || `loaded-${index}`,
          title: prop.title || 'Unknown Property',
          url: prop.url || '#',
          price: prop.price || 'Price TBD',
          location: prop.location || 'Location Unknown',
          description: prop.description || 'No description available',
          score: prop.score || 50,
          bed_count: prop.bed_count || 0,
          acreage: prop.acreage || 0,
          nearest_airport: prop.nearest_airport || 'N/A',
          drive_time_minutes: prop.drive_time_minutes || 0,
          ai_summary: prop.ai_summary || 'Analysis pending...',
          image_url: prop.image_url || '',
          status: prop.status || 'New',
          funnel_stage: prop.funnel_stage || 'discovered',
          is_new: prop.is_new ?? true,
          verification_reason: prop.verification_reason || '',
          source_type: prop.source_type || 'news'
        }));
        setProperties(props);
      }
    } catch (err) {
      console.error('Failed to load properties:', err);
      setError('Failed to load properties');
    }
  };

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        const statusRes = await fetch(`${API_BASE_URL}/`);
        const statusData = await statusRes.json();
        setDbConnected(statusData.database_connected);
        await loadProperties('qualified');
      } catch (err) {
        console.error('Failed to connect:', err);
        setDbConnected(false);
      } finally {
        setInitialLoading(false);
      }
    };
    init();
  }, []);

  // Reload when tab changes
  useEffect(() => {
    if (!initialLoading) {
      loadProperties(activeTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, initialLoading]);

  const runScoutAgent = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/scout/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verify: true })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      await response.json();
      setLastRun(new Date().toLocaleTimeString());
      await loadProperties(activeTab);

    } catch (err) {
      console.error('Scout agent error:', err);
      setError(err instanceof Error ? err.message : 'Failed to run scout agent');
    } finally {
      setLoading(false);
    }
  };

  const runCustomSearch = async () => {
    if (!customQuery.trim()) return;

    setSearchLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/scout/search?query=${encodeURIComponent(customQuery)}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`Search error: ${response.status}`);
      }

      await response.json();
      setLastRun(new Date().toLocaleTimeString());
      setCustomQuery('');
      await loadProperties(activeTab);

    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setSearchLoading(false);
    }
  };

  // Filter properties based on search text
  const filteredProperties = properties.filter(prop =>
    filterText === '' ||
    prop.title.toLowerCase().includes(filterText.toLowerCase()) ||
    prop.location.toLowerCase().includes(filterText.toLowerCase())
  );

  // Update property status
  const updatePropertyStatus = async (propertyId: string, newStatus: string) => {
    setUpdatingId(propertyId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/properties/${propertyId}/status?status=${newStatus}`, {
        method: 'PATCH'
      });

      if (response.ok) {
        setProperties(prev => prev.map(p =>
          p.id === propertyId ? { ...p, status: newStatus } : p
        ));
      }
    } catch (err) {
      console.error('Failed to update property status:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleStar = (propertyId: string) => {
    const prop = properties.find(p => p.id === propertyId);
    const newStatus = prop?.status === 'Starred' ? 'New' : 'Starred';
    updatePropertyStatus(propertyId, newStatus);
  };

  const handleDismiss = async (propertyId: string, reason: string) => {
    setUpdatingId(propertyId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/properties/${propertyId}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });

      if (response.ok) {
        setProperties(prev => prev.filter(p => p.id !== propertyId));
      }
    } catch (err) {
      console.error('Failed to dismiss property:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-200 font-sans">

      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-black/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold tracking-tight flex items-center gap-2">
              <span className="w-3 h-3 bg-blue-600 rounded-full inline-block"></span>
              Edge City Finder
            </h1>
            {dbConnected !== null && (
              <span className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${dbConnected ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                {dbConnected ? <DatabaseZap size={12} /> : <Database size={12} />}
                {dbConnected ? 'Connected' : 'Demo Mode'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {lastRun && (
              <span className="text-xs text-zinc-500">Last run: {lastRun}</span>
            )}
            <button
              onClick={runScoutAgent}
              disabled={loading}
              className="bg-zinc-900 dark:bg-white text-white dark:text-black px-4 py-2 rounded-full text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <><Loader2 size={16} className="animate-spin" /> Searching...</>
              ) : (
                <><RefreshCw size={16} /> Run Scout Agent</>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => setActiveTab('qualified')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'qualified'
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200'
              }`}
          >
            <Sparkles size={16} />
            Qualified Leads
          </button>
          <button
            onClick={() => setActiveTab('interesting')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'interesting'
                ? 'bg-purple-600 text-white'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200'
              }`}
          >
            <Newspaper size={16} />
            Interesting Finds
          </button>
        </div>

        {/* Custom Search */}
        <div className="mb-6 flex gap-2">
          <input
            type="text"
            placeholder="Run a custom search query..."
            value={customQuery}
            onChange={(e) => setCustomQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runCustomSearch()}
            className="flex-1 px-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
          <button
            onClick={runCustomSearch}
            disabled={searchLoading || !customQuery.trim()}
            className="px-4 py-2 bg-zinc-900 dark:bg-white text-white dark:text-black rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
          >
            {searchLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>

        {/* Title and Filter */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">
            {activeTab === 'qualified' ? 'Qualified Leads' : 'Interesting Finds'}
            <span className="ml-2 text-sm font-normal text-zinc-500">
              ({filteredProperties.length} properties)
            </span>
          </h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={16} />
            <input
              type="text"
              placeholder="Filter..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="pl-10 pr-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        </div>

        {/* Loading State */}
        {(loading || initialLoading) && (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <Loader2 size={40} className="animate-spin mb-4" />
            <p className="text-lg font-medium">
              {initialLoading ? 'Loading properties...' : 'Scout Agent is searching...'}
            </p>
          </div>
        )}

        {/* Properties List */}
        {!loading && !initialLoading && (
          <div className="space-y-1">
            {/* Table Header */}
            {filteredProperties.length > 0 && (
              <div className="flex items-center text-[10px] uppercase tracking-wide text-zinc-400 font-medium px-1 mb-2">
                <div className="w-20 flex-shrink-0 text-center">Image</div>
                <div className="w-12 flex-shrink-0 text-center">Score</div>
                <div className="flex-1 pl-3">Property</div>
                <div className="w-16 flex-shrink-0 text-center">Beds</div>
                <div className="w-16 flex-shrink-0 text-center">Acres</div>
                <div className="w-20 flex-shrink-0 text-center">Price</div>
                <div className="w-14 flex-shrink-0 text-center">Source</div>
                <div className="w-[72px] flex-shrink-0 text-center">Actions</div>
              </div>
            )}
            {filteredProperties.length === 0 ? (
              <div className="text-center py-20 text-zinc-500">
                <p className="text-lg font-medium">No properties found</p>
                <p className="text-sm">Run the Scout Agent to find properties</p>
              </div>
            ) : (
              filteredProperties.map((prop) => (
                <PropertyCard
                  key={prop.id}
                  {...prop}
                  onStar={handleStar}
                  onDismiss={handleDismiss}
                  isUpdating={updatingId === prop.id}
                />
              ))
            )}
          </div>
        )}
      </main>

    </div>
  );
}
