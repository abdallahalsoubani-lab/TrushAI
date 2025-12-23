"use client";

/**
 * Batch Item Details Page - View Individual Item Analysis
 * =======================================================
 * Displays detailed information about a specific batch item.
 *
 * Features:
 * - Item metadata and analysis results
 * - Original image display
 * - Overlay image with detections
 * - Artifacts list with download links
 * - Status and confidence information
 * - Link back to batch details
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import '../../globals.css';

// Type for batch item
interface BatchItem {
  id: number;
  batch_id: number;
  original_filename: string;
  stored_path: string;
  status: 'EMPTY' | 'HALF' | 'FULL' | 'NO_BIN_DETECTED';
  confidence: number;
  bins_detected: number;
  created_at: string;
  completed_at: string | null;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  artifacts: Artifact[];
}

// Type for artifact
interface Artifact {
  id: number;
  type: 'overlay' | 'cropped_bin' | 'debug_json';
  path: string;
  bin_index: number | null;
  file_size: number | null;
  mime_type: string | null;
}

export default function BatchItemDetailsPage() {
  const params = useParams();
  const itemId = params.id as string;

  const [item, setItem] = useState<BatchItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch item details
  useEffect(() => {
    const fetchItem = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/batch-items/${itemId}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch item details');
        }

        const data: BatchItem = await response.json();
        setItem(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load item');
      } finally {
        setLoading(false);
      }
    };

    fetchItem();
  }, [itemId]);

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

  // Format file size
  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Get artifact type label
  const getArtifactTypeLabel = (type: string): string => {
    switch (type) {
      case 'overlay':
        return 'Overlay Image';
      case 'cropped_bin':
        return 'Cropped Bin';
      case 'debug_json':
        return 'Debug JSON';
      default:
        return type;
    }
  };

  // Get artifact URL
  const getArtifactUrl = (path: string): string => {
    return `http://localhost:8000/api/v1/artifacts/${encodeURIComponent(path)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading item details...</p>
        </div>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
            <h1 className="text-3xl font-bold text-gray-900">Item Not Found</h1>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-medium">Error</p>
            <p className="text-sm text-red-600 mt-1">{error || 'Item not found'}</p>
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

  // Find overlay artifact
  const overlayArtifact = item.artifacts.find((a) => a.type === 'overlay');
  const croppedBins = item.artifacts.filter((a) => a.type === 'cropped_bin');
  const debugArtifact = item.artifacts.find((a) => a.type === 'debug_json');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Item #{item.id}</h1>
              <p className="text-sm font-mono text-gray-500 mt-1">
                {item.original_filename}
              </p>
            </div>
            <div className="flex gap-2">
              <Link
                href={`/batches/${item.batch_id}`}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Back to Batch
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Images */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overlay Image */}
            {overlayArtifact && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Analysis Result
                </h2>
                <div className="bg-gray-100 rounded-lg overflow-hidden">
                  <img
                    src={getArtifactUrl(overlayArtifact.path)}
                    alt="Overlay"
                    className="w-full h-auto"
                  />
                </div>
                <div className="mt-4 flex justify-between items-center">
                  <p className="text-sm text-gray-500">
                    {overlayArtifact.mime_type} •{' '}
                    {formatFileSize(overlayArtifact.file_size)}
                  </p>
                  <a
                    href={getArtifactUrl(overlayArtifact.path)}
                    download
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
                  >
                    Download
                  </a>
                </div>
              </div>
            )}

            {/* Cropped Bins */}
            {croppedBins.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Detected Bins ({croppedBins.length})
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {croppedBins.map((bin, index) => (
                    <div key={bin.id} className="border border-gray-200 rounded-lg overflow-hidden">
                      <img
                        src={getArtifactUrl(bin.path)}
                        alt={`Bin ${bin.bin_index !== null ? bin.bin_index + 1 : index + 1}`}
                        className="w-full h-32 object-cover"
                      />
                      <div className="p-2 bg-gray-50">
                        <p className="text-xs text-gray-600">
                          Bin {bin.bin_index !== null ? bin.bin_index + 1 : index + 1}
                        </p>
                        <a
                          href={getArtifactUrl(bin.path)}
                          download
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Download
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Details */}
          <div className="space-y-6">
            {/* Analysis Results */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Analysis Results
              </h2>

              {/* Status Badge */}
              <div className="mb-6">
                <p className="text-sm text-gray-500 mb-2">Fill Level Status</p>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-4 h-4 rounded-full ${getStatusColor(item.status)}`}
                  ></div>
                  <span
                    className={`text-2xl font-bold ${getStatusTextColor(item.status)}`}
                  >
                    {formatStatus(item.status)}
                  </span>
                </div>
              </div>

              {/* Confidence */}
              <div className="mb-6">
                <p className="text-sm text-gray-500 mb-2">Confidence</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${item.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    {(item.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Bins Detected</span>
                  <span className="font-medium text-gray-900">{item.bins_detected}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Processing Status</span>
                  <span className="font-medium text-gray-900 capitalize">
                    {item.processing_status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Created At</span>
                  <span className="font-medium text-gray-900">
                    {formatDate(item.created_at)}
                  </span>
                </div>
                {item.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Completed At</span>
                    <span className="font-medium text-gray-900">
                      {formatDate(item.completed_at)}
                    </span>
                  </div>
                )}
              </div>

              {/* Error Message */}
              {item.error_message && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm font-medium text-red-800">Error</p>
                  <p className="text-sm text-red-600 mt-1">{item.error_message}</p>
                </div>
              )}
            </div>

            {/* Artifacts */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Artifacts ({item.artifacts.length})
              </h2>

              {item.artifacts.length === 0 ? (
                <p className="text-sm text-gray-500">No artifacts available</p>
              ) : (
                <div className="space-y-3">
                  {item.artifacts.map((artifact) => (
                    <div
                      key={artifact.id}
                      className="p-3 bg-gray-50 border border-gray-200 rounded-lg"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {getArtifactTypeLabel(artifact.type)}
                            {artifact.bin_index !== null && ` #${artifact.bin_index + 1}`}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {artifact.mime_type} •{' '}
                            {formatFileSize(artifact.file_size)}
                          </p>
                        </div>
                        <a
                          href={getArtifactUrl(artifact.path)}
                          download
                          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Download
                        </a>
                      </div>
                      <p className="text-xs font-mono text-gray-400 truncate">
                        {artifact.path}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* File Info */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">File Info</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-500 mb-1">Original Filename</p>
                  <p className="font-mono text-xs text-gray-900 break-all">
                    {item.original_filename}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 mb-1">Stored Path</p>
                  <p className="font-mono text-xs text-gray-900 break-all">
                    {item.stored_path}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 mb-1">Batch ID</p>
                  <Link
                    href={`/batches/${item.batch_id}`}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Batch #{item.batch_id}
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
