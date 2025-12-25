"use client";

/**
 * Smart Waste Monitoring Dashboard
 * =================================
 * Main page component for displaying trash bin statuses.
 *
 * Features:
 * - Real-time bin status display
 * - Auto-refresh every 5 seconds
 * - Color-coded fill levels (Green=Empty, Orange=Half, Red=Full)
 * - Bin count statistics
 * - Manual refresh button
 *
 * TODO: Add filtering by fill level
 * TODO: Add sorting options
 * TODO: Add search functionality
 * TODO: Add detailed bin view (modal)
 * TODO: Add historical data charts
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import './globals.css';

// Type definitions matching the backend API
interface BinStatus {
  bin_id: string;
  fill_level: 'EMPTY' | 'HALF' | 'FULL';
  confidence: number;
  location: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  } | null;
  last_updated: string;
  detection_count: number;
}

interface BinsResponse {
  bins: BinStatus[];
  total_bins: number;
  timestamp: string;
}

interface DashboardArea {
  area_id: number;
  area_name: string;
  bins_count: number;
  captures_count: number;
  max_priority: number;
  last_seen: string | null;
}

export default function Home() {
  const [bins, setBins] = useState<BinStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [areas, setAreas] = useState<DashboardArea[]>([]);
  const [areasError, setAreasError] = useState<string | null>(null);
  const [areasLoading, setAreasLoading] = useState<boolean>(false);
  const [areasToast, setAreasToast] = useState<string | null>(null);

  // Fetch bin status from API
  const fetchBinStatus = async () => {
    try {
      setError(null);
      const response = await fetch('http://localhost:8000/api/v1/bins-status');

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data: BinsResponse = await response.json();
      setBins(data.bins);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      setLoading(false);
    }
  };

  const fetchAreas = async () => {
    try {
      setAreasError(null);
      setAreasLoading(true);
      const response = await fetch('http://localhost:8000/api/v1/dashboard/areas');
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      const data = await response.json();
      setAreas(data.areas || []);
    } catch (err) {
      setAreasError(err instanceof Error ? err.message : 'Failed to fetch areas');
    } finally {
      setAreasLoading(false);
    }
  };

  const deleteArea = async (areaId: number) => {
    if (!window.confirm("Delete area and all its bins/captures?")) return;
    try {
      const res = await fetch(`http://localhost:8000/api/v1/areas/${areaId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete area");
      setAreasToast("Area deleted");
      fetchAreas();
    } catch (err) {
      setAreasError(err instanceof Error ? err.message : "Failed to delete area");
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchBinStatus();
    fetchAreas();
    const toastMsg = window.localStorage.getItem("areas_toast");
    if (toastMsg) {
      setAreasToast(toastMsg);
      window.localStorage.removeItem("areas_toast");
    }
  }, []);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchBinStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  useEffect(() => {
    if (!areasToast) return;
    const timer = setTimeout(() => setAreasToast(null), 2500);
    return () => clearTimeout(timer);
  }, [areasToast]);


  // Get fill level color
  const getFillLevelColor = (level: string): string => {
    switch (level) {
      case 'EMPTY':
        return 'bg-green-500';
      case 'HALF':
        return 'bg-orange-500';
      case 'FULL':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Get fill level text color
  const getFillLevelTextColor = (level: string): string => {
    switch (level) {
      case 'EMPTY':
        return 'text-green-600';
      case 'HALF':
        return 'text-orange-600';
      case 'FULL':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  // Calculate statistics
  const stats = {
    total: bins.length,
    empty: bins.filter((b) => b.fill_level === 'EMPTY').length,
    half: bins.filter((b) => b.fill_level === 'HALF').length,
    full: bins.filter((b) => b.fill_level === 'FULL').length,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Smart Waste Monitoring
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                AI-Powered Trash Bin Fill Level Detection
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/upload"
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                Upload File
              </Link>
              <Link
                href="/walk-scan"
                className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition"
              >
                Walk Scan
              </Link>
              <Link
                href="/bins"
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
              >
                Bins
              </Link>
              <Link
                href="/train"
                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition"
              >
                Train Model
              </Link>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                Auto-refresh
              </label>
              <button
                onClick={fetchBinStatus}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Bins</div>
            <div className="mt-2 text-3xl font-bold text-gray-900">
              {stats.total}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Empty</div>
            <div className="mt-2 text-3xl font-bold text-green-600">
              {stats.empty}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Half Full</div>
            <div className="mt-2 text-3xl font-bold text-orange-600">
              {stats.half}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Full</div>
            <div className="mt-2 text-3xl font-bold text-red-600">
              {stats.full}
            </div>
          </div>
        </div>

        {/* Last Update Info */}
        {lastUpdate && (
          <div className="mb-4 text-sm text-gray-500">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading bin status...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-800">Error: {error}</p>
            <p className="text-sm text-red-600 mt-2">
              Make sure the backend API is running on http://localhost:8000
            </p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && bins.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600 text-lg">No bins detected yet</p>
            <p className="text-sm text-gray-500 mt-2">
              Analyze a video using the API to see bin statuses
            </p>
          </div>
        )}

        {/* Bins Grid */}
        {!loading && bins.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {bins.map((bin) => (
              <div
                key={bin.bin_id}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition p-6"
              >
                {/* Bin ID and Status Indicator */}
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {bin.bin_id}
                  </h3>
                  <div
                    className={`w-3 h-3 rounded-full ${getFillLevelColor(
                      bin.fill_level
                    )}`}
                  ></div>
                </div>

                {/* Fill Level */}
                <div className="mb-4">
                  <div className="text-sm text-gray-500 mb-1">Fill Level</div>
                  <div
                    className={`text-2xl font-bold ${getFillLevelTextColor(
                      bin.fill_level
                    )}`}
                  >
                    {bin.fill_level}
                  </div>
                </div>

                {/* Confidence */}
                <div className="mb-4">
                  <div className="text-sm text-gray-500 mb-1">Confidence</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${bin.confidence * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {(bin.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Detection Count */}
                <div className="text-sm text-gray-500">
                  Detected in {bin.detection_count} frame
                  {bin.detection_count !== 1 ? 's' : ''}
                </div>
              </div>
            ))}
          </div>
        )}

        <section className="mt-12">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-semibold text-gray-900">Areas</h2>
            <button
              onClick={fetchAreas}
              className="text-sm text-blue-600 hover:underline"
            >
              Refresh
            </button>
          </div>

          {areasError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800">Error: {areasError}</p>
            </div>
          )}
          {areasToast && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <p className="text-green-800">{areasToast}</p>
            </div>
          )}

          {areasLoading && (
            <div className="text-sm text-gray-500 mb-4">Loading areas...</div>
          )}

          <div className="space-y-3">
            {areas.map((area) => (
              <div key={area.area_id} className="bg-white rounded-lg shadow-sm border p-3 flex flex-col md:flex-row gap-4">
                <div className="flex-1 text-xs text-gray-700 space-y-1">
                  <div className="text-sm font-semibold">{area.area_name}</div>
                  <div>Bins: {area.bins_count}</div>
                  <div>Captures: {area.captures_count}</div>
                  <div>Max priority: {area.max_priority.toFixed(0)}</div>
                  <div className="text-gray-500">
                    Last seen: {area.last_seen ? new Date(area.last_seen).toLocaleString() : "-"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    href={`/areas/${area.area_id}`}
                    className="px-3 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
                  >
                    Open
                  </Link>
                  <button
                    onClick={() => deleteArea(area.area_id)}
                    className="px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
            {areas.length === 0 && !areasLoading && (
              <div className="text-sm text-gray-500">No areas yet.</div>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-12 py-6 text-center text-sm text-gray-500">
        <p>Smart Waste Monitoring MVP • Powered by YOLOv8 & Computer Vision</p>
        <p className="mt-1">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            API Documentation
          </a>
        </p>
      </footer>
    </div>
  );
}
