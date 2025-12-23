"use client";

/**
 * Batch Details Page - View Individual Batch Analysis
 * ===================================================
 * Displays detailed information about a specific batch upload.
 *
 * Features:
 * - Batch metadata and summary
 * - Status counts breakdown
 * - Paginated table of batch items
 * - Item thumbnails and results
 * - Links to individual item details
 * - Processing status and errors
 * - Download options
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import '../../globals.css';

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

// Type for batch item
interface BatchItem {
  id: number;
  original_filename: string;
  stored_path: string;
  status: 'EMPTY' | 'HALF' | 'FULL' | 'NO_BIN_DETECTED';
  confidence: number;
  bins_detected: number;
  created_at: string;
  completed_at: string | null;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
}

// API response types
interface BatchDetailsResponse {
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
  processing_status: string;
  error_message: string | null;
  failed_count: number;
}

interface BatchItemsResponse {
  items: BatchItem[];
  total: number;
  skip: number;
  limit: number;
}

export default function BatchDetailsPage() {
  const params = useParams();
  const batchId = params.id as string;

  const [batch, setBatch] = useState<Batch | null>(null);
  const [items, setItems] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [itemsLoading, setItemsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);
  const limit = 50;

  // Fetch batch details
  useEffect(() => {
    const fetchBatch = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`http://localhost:8000/api/v1/batches/${batchId}`);

        if (!response.ok) {
          throw new Error('Failed to fetch batch details');
        }

        const data: BatchDetailsResponse = await response.json();
        setBatch(data as Batch);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load batch');
      } finally {
        setLoading(false);
      }
    };

    fetchBatch();
  }, [batchId]);

  // Fetch batch items
  useEffect(() => {
    const fetchItems = async () => {
      setItemsLoading(true);

      try {
        const skip = (page - 1) * limit;
        const response = await fetch(
          `http://localhost:8000/api/v1/batches/${batchId}/items?skip=${skip}&limit=${limit}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch batch items');
        }

        const data: BatchItemsResponse = await response.json();
        setItems(data.items);
        setTotalItems(data.total);
      } catch (err) {
        console.error('Failed to load items:', err);
      } finally {
        setItemsLoading(false);
      }
    };

    if (batch) {
      fetchItems();
    }
  }, [batchId, batch, page]);

  // Format date
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Get status color
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'EMPTY':
        return 'bg-green-500';
      case 'HALF':
        return 'bg-orange-500';
      case 'FULL':
        return 'bg-red-500';
      case 'NO_BIN_DETECTED':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Get status text color
  const getStatusTextColor = (status: string): string => {
    switch (status) {
      case 'EMPTY':
        return 'text-green-600';
      case 'HALF':
        return 'text-orange-600';
      case 'FULL':
        return 'text-red-600';
      case 'NO_BIN_DETECTED':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  // Format status text
  const formatStatus = (status: string): string => {
    return status.replace(/_/g, ' ');
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
  const totalPages = Math.ceil(totalItems / limit);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading batch details...</p>
        </div>
      </div>
    );
  }

  if (error || !batch) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
            <h1 className="text-3xl font-bold text-gray-900">Batch Not Found</h1>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-medium">Error</p>
            <p className="text-sm text-red-600 mt-1">
              {error || 'Batch not found'}
            </p>
          </div>
          <Link
            href="/batches"
            className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Back to Batches
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-900">
                  Batch #{batch.id}
                </h1>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusBadgeColor(
                    batch.processing_status
                  )}`}
                >
                  {batch.processing_status.toUpperCase()}
                </span>
              </div>
              <p className="text-sm font-mono text-gray-500">{batch.batch_id}</p>
            </div>
            <div className="flex gap-2">
              <Link
                href="/batches"
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Back to Batches
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Batch Summary Card */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Summary</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div>
              <p className="text-sm text-gray-500">Created At</p>
              <p className="text-lg font-medium text-gray-900">
                {formatDate(batch.created_at)}
              </p>
            </div>
            {batch.completed_at && (
              <div>
                <p className="text-sm text-gray-500">Completed At</p>
                <p className="text-lg font-medium text-gray-900">
                  {formatDate(batch.completed_at)}
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-500">Total Files</p>
              <p className="text-lg font-medium text-gray-900">{batch.total_files}</p>
            </div>
          </div>

          {/* Status Counts */}
          {batch.processing_status === 'completed' && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Fill Level Distribution
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <p className="text-xs text-gray-600">EMPTY</p>
                  </div>
                  <p className="text-3xl font-bold text-green-600">
                    {batch.status_counts.EMPTY}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {((batch.status_counts.EMPTY / batch.total_files) * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <p className="text-xs text-gray-600">HALF</p>
                  </div>
                  <p className="text-3xl font-bold text-orange-600">
                    {batch.status_counts.HALF}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {((batch.status_counts.HALF / batch.total_files) * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <p className="text-xs text-gray-600">FULL</p>
                  </div>
                  <p className="text-3xl font-bold text-red-600">
                    {batch.status_counts.FULL}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {((batch.status_counts.FULL / batch.total_files) * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                    <p className="text-xs text-gray-600">NO BIN</p>
                  </div>
                  <p className="text-3xl font-bold text-gray-600">
                    {batch.status_counts.NO_BIN_DETECTED}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {((batch.status_counts.NO_BIN_DETECTED / batch.total_files) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {batch.error_message && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm font-medium text-red-800">Error</p>
              <p className="text-sm text-red-600 mt-1">{batch.error_message}</p>
            </div>
          )}

          {/* Failed Count */}
          {batch.failed_count > 0 && (
            <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-sm text-orange-800">
                {batch.failed_count} file{batch.failed_count !== 1 ? 's' : ''} failed to
                process
              </p>
            </div>
          )}
        </div>

        {/* Items Table */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Batch Items ({totalItems})
            </h2>
          </div>

          {itemsLoading ? (
            <div className="p-12 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading items...</p>
            </div>
          ) : items.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-gray-500">No items found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Filename
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Confidence
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Bins
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          #{item.id}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          <div className="font-mono text-xs truncate max-w-xs">
                            {item.original_filename}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusTextColor(
                              item.status
                            )}`}
                          >
                            <div
                              className={`w-2 h-2 rounded-full ${getStatusColor(
                                item.status
                              )}`}
                            ></div>
                            {formatStatus(item.status)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {(item.confidence * 100).toFixed(0)}%
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {item.bins_detected}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <Link
                            href={`/batch-items/${item.id}`}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            View Details →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    Showing {(page - 1) * limit + 1} to{' '}
                    {Math.min(page * limit, totalItems)} of {totalItems} items
                  </div>
                  <div className="flex items-center gap-2">
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
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
