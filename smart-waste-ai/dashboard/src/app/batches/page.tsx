"use client";

/**
 * Batches List Page - View All Batch Uploads
 * ==========================================
 * Displays a paginated list of all batch image uploads.
 *
 * Features:
 * - Paginated batch list with recent batches first
 * - Status filtering (all/processing/completed/failed)
 * - Batch summary cards with status counts
 * - Link to individual batch details
 * - Processing status indicators
 * - Created/completed timestamps
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import '../globals.css';

// Type for batch analysis
interface Batch {
  id: number;
  batch_id: string;
  total_files: number;
  status_counts: {
    EMPTY: number;
    HALF: number;
    FULL: number;
    NO_BIN_DETECTED: number;
  };
  created_at: string;
  completed_at: string | null;
  processing_status: 'processing' | 'completed' | 'failed';
  error_message: string | null;
  failed_count: number;
}

// API response type
interface BatchesResponse {
  batches: Batch[];
  total: number;
  skip: number;
  limit: number;
}

export default function BatchesPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [total, setTotal] = useState<number>(0);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const limit = 20;

  // Fetch batches
  useEffect(() => {
    const fetchBatches = async () => {
      setLoading(true);
      setError(null);

      try {
        const skip = (page - 1) * limit;
        const filterParam = statusFilter !== 'all' ? `&status=${statusFilter}` : '';
        const response = await fetch(
          `http://localhost:8000/api/v1/batches?skip=${skip}&limit=${limit}${filterParam}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch batches');
        }

        const data: BatchesResponse = await response.json();
        setBatches(data.batches);
        setTotal(data.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load batches');
      } finally {
        setLoading(false);
      }
    };

    fetchBatches();
  }, [page, statusFilter]);

  // Format date
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Get status badge color
  const getStatusBadgeColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'processing':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Calculate total pages
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Batch Uploads</h1>
              <p className="text-sm text-gray-500 mt-1">
                View and manage batch image analysis results
              </p>
            </div>
            <div className="flex gap-2">
              <Link
                href="/upload"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                New Upload
              </Link>
              <Link
                href="/"
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Filters */}
        <div className="mb-6 bg-white rounded-lg shadow-md p-4">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">Filter by Status:</span>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setStatusFilter('all');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg transition font-medium ${
                  statusFilter === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                All
              </button>
              <button
                onClick={() => {
                  setStatusFilter('completed');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg transition font-medium ${
                  statusFilter === 'completed'
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Completed
              </button>
              <button
                onClick={() => {
                  setStatusFilter('processing');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg transition font-medium ${
                  statusFilter === 'processing'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Processing
              </button>
              <button
                onClick={() => {
                  setStatusFilter('failed');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg transition font-medium ${
                  statusFilter === 'failed'
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Failed
              </button>
            </div>
            <span className="text-sm text-gray-500 ml-auto">
              Total: {total} batch{total !== 1 ? 'es' : ''}
            </span>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading batches...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-medium">Error</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        )}

        {/* Batches List */}
        {!loading && !error && (
          <>
            {batches.length === 0 ? (
              <div className="bg-white rounded-lg shadow-md p-12 text-center">
                <p className="text-gray-500 text-lg">No batches found</p>
                <p className="text-sm text-gray-400 mt-2">
                  Upload your first batch to get started
                </p>
                <Link
                  href="/upload"
                  className="mt-4 inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  Upload Batch
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {batches.map((batch) => (
                  <div
                    key={batch.id}
                    className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            Batch #{batch.id}
                          </h3>
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusBadgeColor(
                              batch.processing_status
                            )}`}
                          >
                            {batch.processing_status.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm font-mono text-gray-500 mb-2">
                          {batch.batch_id}
                        </p>
                        <div className="flex gap-6 text-sm text-gray-600">
                          <div>
                            <span className="text-gray-500">Created:</span>{' '}
                            {formatDate(batch.created_at)}
                          </div>
                          {batch.completed_at && (
                            <div>
                              <span className="text-gray-500">Completed:</span>{' '}
                              {formatDate(batch.completed_at)}
                            </div>
                          )}
                          <div>
                            <span className="text-gray-500">Total Files:</span>{' '}
                            {batch.total_files}
                          </div>
                        </div>
                      </div>
                      <Link
                        href={`/batches/${batch.id}`}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
                      >
                        View Details
                      </Link>
                    </div>

                    {/* Status Counts */}
                    {batch.processing_status === 'completed' && (
                      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-green-500"></div>
                          <div>
                            <p className="text-xs text-gray-500">EMPTY</p>
                            <p className="text-lg font-bold text-green-600">
                              {batch.status_counts.EMPTY}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                          <div>
                            <p className="text-xs text-gray-500">HALF</p>
                            <p className="text-lg font-bold text-orange-600">
                              {batch.status_counts.HALF}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-red-500"></div>
                          <div>
                            <p className="text-xs text-gray-500">FULL</p>
                            <p className="text-lg font-bold text-red-600">
                              {batch.status_counts.FULL}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                          <div>
                            <p className="text-xs text-gray-500">NO BIN</p>
                            <p className="text-lg font-bold text-gray-600">
                              {batch.status_counts.NO_BIN_DETECTED}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Error Message */}
                    {batch.error_message && (
                      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-800">{batch.error_message}</p>
                      </div>
                    )}

                    {/* Failed Count */}
                    {batch.failed_count > 0 && (
                      <div className="mt-2">
                        <p className="text-sm text-orange-600">
                          {batch.failed_count} file{batch.failed_count !== 1 ? 's' : ''}{' '}
                          failed to process
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-sm text-gray-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
