"use client";

/**
 * Upload Page - File Upload and Analysis
 * =======================================
 * Allows users to upload video/image files or multiple images for batch analysis.
 *
 * Features:
 * - Single file upload: video (.mp4, .avi, .mov) or image (.jpg, .png)
 * - Batch upload: multiple images (.jpg, .png, .webp)
 * - File preview (image preview or filename for video)
 * - Thumbnails grid for batch upload
 * - Analyze button with loading state
 * - Batch progress tracking
 * - Result display with color-coded status
 * - Batch summary with link to details page
 * - Clear button to reset and upload another file
 *
 * TODO: Add drag-and-drop file upload
 */

import { useState } from 'react';
import Link from 'next/link';
import '../globals.css';

// Type for upload analysis response
interface UploadResult {
  input_type: string;
  status: 'EMPTY' | 'HALF' | 'FULL' | 'NO_BIN_DETECTED';
  confidence: number;
  bins_detected: number;
  message?: string;
  frames_analyzed?: number;
  frame_indices?: number[];
  sampling_strategy?: string;
  debug_artifacts?: {
    overlay_image?: string;
    cropped_bins?: string[];
    metadata?: string;
    frames?: string[];
    annotated?: string[];
  };
  metadata?: {
    detections_summary?: Array<{ frame_index: number; count: number }>;
  };
}

// Type for batch upload response
interface BatchUploadResult {
  batch_id: string;
  total_files: number;
  status_counts: {
    EMPTY: number;
    HALF: number;
    FULL: number;
    NO_BIN_DETECTED: number;
  };
  items: Array<{
    id: number;
    filename: string;
    status: 'EMPTY' | 'HALF' | 'FULL' | 'NO_BIN_DETECTED';
    confidence: number;
    bins_detected: number;
  }>;
  internal_batch_id?: number;
}

export default function UploadPage() {
  // Upload mode: 'single' or 'batch'
  const [uploadMode, setUploadMode] = useState<'single' | 'batch'>('single');

  // Single file upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [debugEnabled, setDebugEnabled] = useState<boolean>(false);
  const [serviceInfo, setServiceInfo] = useState<any | null>(null);
  const [debugOpen, setDebugOpen] = useState<boolean>(false);

  // Batch upload state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [filePreviews, setFilePreviews] = useState<string[]>([]);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);
  const [batchResult, setBatchResult] = useState<BatchUploadResult | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = [
      'video/mp4',
      'video/avi',
      'video/quicktime', // .mov
      'image/jpeg',
      'image/jpg',
      'image/png',
    ];

    if (!validTypes.includes(file.type)) {
      setError(
        'Invalid file type. Please upload a video (MP4, AVI, MOV) or image (JPG, PNG).'
      );
      return;
    }

    setSelectedFile(file);
    setError(null);
    setResult(null);

    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setPreviewUrl(null);
    }
  };

  // Handle file upload and analysis
  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('debug', debugEnabled ? 'true' : 'false');

      // Upload and analyze
      const response = await fetch('http://localhost:8000/api/v1/analyze-upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data: UploadResult = await response.json();
      setResult(data);

      const infoRes = await fetch('http://localhost:8000/api/v1/service-info');
      if (infoRes.ok) {
        const infoData = await infoRes.json();
        setServiceInfo(infoData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze file');
    } finally {
      setLoading(false);
    }
  };

  // Reset form
  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setDebugEnabled(false);
    setServiceInfo(null);
    setDebugOpen(false);
    setSelectedFiles([]);
    setFilePreviews([]);
    setBatchResult(null);
    setBatchError(null);
  };

  const handleCopyDebugReport = async () => {
    if (!result || !selectedFile) return;
    const report = {
      timestamp: new Date().toISOString(),
      request: {
        endpoint: 'POST /api/v1/analyze-upload',
        debug: debugEnabled,
        filename: selectedFile.name,
        size_bytes: selectedFile.size,
      },
      response: result,
      service_info: {
        detector_weights: serviceInfo?.detector_weights,
        detector_classes: serviceInfo?.detector_classes,
        confidence_threshold: serviceInfo?.detector_info?.confidence_threshold,
        device: serviceInfo?.detector_info?.device,
      },
    };
    await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
  };

  // Handle multiple file selection for batch upload
  const handleBatchFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    // Validate all files are images
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    const invalidFiles = files.filter(file => !validTypes.includes(file.type));

    if (invalidFiles.length > 0) {
      setBatchError(
        `Invalid file types detected. Only images (JPG, PNG, WEBP) are allowed for batch upload. Invalid: ${invalidFiles.map(f => f.name).join(', ')}`
      );
      return;
    }

    setSelectedFiles(files);
    setBatchError(null);
    setBatchResult(null);

    // Create previews for all images
    const previews: string[] = [];
    let loadedCount = 0;

    files.forEach((file, index) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        previews[index] = reader.result as string;
        loadedCount++;
        if (loadedCount === files.length) {
          setFilePreviews([...previews]);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  // Handle batch upload and analysis
  const handleBatchAnalyze = async () => {
    if (selectedFiles.length === 0) return;

    setBatchLoading(true);
    setBatchError(null);
    setBatchResult(null);

    try {
      // Create FormData with multiple files
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      // Upload and analyze batch
      const response = await fetch('http://localhost:8000/api/v1/analyze-batch-upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Batch analysis failed');
      }

      const data: BatchUploadResult = await response.json();
      setBatchResult(data);
    } catch (err) {
      setBatchError(err instanceof Error ? err.message : 'Failed to analyze batch');
    } finally {
      setBatchLoading(false);
    }
  };

  // Switch upload mode and clear state
  const switchMode = (mode: 'single' | 'batch') => {
    handleClear();
    setUploadMode(mode);
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

  // Format status text for display
  const formatStatus = (status: string): string => {
    // Replace underscores with spaces and title case
    return status.replace(/_/g, ' ');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Upload & Analyze
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Upload images or videos to detect trash bin fill levels
              </p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Mode Toggle */}
        <div className="mb-6 bg-white rounded-lg shadow-md p-4">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">Upload Mode:</span>
            <div className="flex gap-2">
              <button
                onClick={() => switchMode('single')}
                className={`px-4 py-2 rounded-lg transition font-medium ${
                  uploadMode === 'single'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Single File
              </button>
              <button
                onClick={() => switchMode('batch')}
                className={`px-4 py-2 rounded-lg transition font-medium ${
                  uploadMode === 'batch'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Batch Upload
              </button>
            </div>
            <span className="text-xs text-gray-500">
              {uploadMode === 'single' ? '(Video or Image)' : '(Multiple Images)'}
            </span>
          </div>
        </div>

        {/* Single File Upload Card */}
        {uploadMode === 'single' && (
          <div className="bg-white rounded-lg shadow-md p-8">
          {/* File Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select File
            </label>
            <input
              type="file"
              accept="video/mp4,video/avi,video/quicktime,image/jpeg,image/jpg,image/png"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <p className="mt-2 text-xs text-gray-500">
              Supported formats: MP4, AVI, MOV (video) | JPG, PNG (image)
            </p>
          </div>

          {/* Preview */}
          {selectedFile && (
            <div className="mb-6">
              <p className="text-sm font-medium text-gray-700 mb-2">Preview</p>
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="max-w-full h-auto max-h-96 rounded-lg border border-gray-300"
                />
              ) : (
                <div className="bg-gray-100 p-4 rounded-lg border border-gray-300">
                  <p className="text-sm text-gray-600">
                    📹 {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Debug Toggle */}
          <div className="mb-6 flex items-center gap-3">
            <input
              id="debug-toggle"
              type="checkbox"
              checked={debugEnabled}
              onChange={(e) => setDebugEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="debug-toggle" className="text-sm text-gray-700">
              Debug mode (save random frames + annotated detections)
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={handleAnalyze}
              disabled={!selectedFile || loading}
              className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition font-medium"
            >
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
            <button
              onClick={handleClear}
              disabled={loading}
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:cursor-not-allowed transition"
            >
              Clear
            </button>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="mt-6 text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">
                Analyzing {selectedFile?.type.startsWith('video') ? 'video' : 'image'}...
              </p>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          )}

          {/* Result Display */}
          {result && (
            <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Analysis Result
              </h3>

              {/* Status Badge */}
              <div className="flex items-center gap-4 mb-4">
                <div
                  className={`w-4 h-4 rounded-full ${getStatusColor(
                    result.status
                  )}`}
                ></div>
                <div>
                  <p className="text-sm text-gray-500">Fill Level Status</p>
                  <p
                    className={`text-3xl font-bold ${getStatusTextColor(
                      result.status
                    )}`}
                  >
                    {formatStatus(result.status)}
                  </p>
                </div>
              </div>

              {/* Confidence */}
              <div className="mb-4">
                <p className="text-sm text-gray-500 mb-1">Confidence</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${result.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    {(result.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Additional Info */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Input Type</p>
                  <p className="font-medium text-gray-900 capitalize">
                    {result.input_type}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Bins Detected</p>
                  <p className="font-medium text-gray-900">
                    {result.bins_detected}
                  </p>
                </div>
              </div>

              {result.message && (
                <p className="mt-4 text-sm text-gray-600">{result.message}</p>
              )}

              {result.frames_analyzed !== undefined && (
                <p className="mt-2 text-xs text-gray-500">
                  Frames analyzed: {result.frames_analyzed} (indices: {result.frame_indices?.join(', ') || '-'})
                </p>
              )}

              {result.status === 'NO_BIN_DETECTED' && (
                <p className="mt-2 text-xs text-orange-600">
                  Tip: Try increasing max_frames or switching sampling strategy.
                </p>
              )}

              <div className="mt-6 border-t border-gray-200 pt-4">
                <button
                  onClick={() => setDebugOpen(!debugOpen)}
                  className="text-sm text-blue-700 hover:text-blue-900"
                >
                  {debugOpen ? 'Hide Debug Report' : 'Show Debug Report'}
                </button>

                {debugOpen && (
                  <div className="mt-3 text-xs text-gray-700 space-y-2">
                    <div>
                      <span className="text-gray-500">Status:</span> {result.status} |{' '}
                      <span className="text-gray-500">Bins:</span> {result.bins_detected} |{' '}
                      <span className="text-gray-500">Confidence:</span> {result.confidence}
                    </div>
                    {result.message && (
                      <div>
                        <span className="text-gray-500">Message:</span> {result.message}
                      </div>
                    )}
                    {result.frames_analyzed !== undefined && (
                      <div>
                        <span className="text-gray-500">Frames analyzed:</span>{' '}
                        {result.frames_analyzed} |{' '}
                        <span className="text-gray-500">Indices:</span>{' '}
                        {result.frame_indices?.join(', ') || '-'} |{' '}
                        <span className="text-gray-500">Strategy:</span>{' '}
                        {result.sampling_strategy || '-'}
                      </div>
                    )}
                    {serviceInfo && (
                      <div>
                        <span className="text-gray-500">Detector weights:</span>{' '}
                        {serviceInfo?.detector_weights || '-'} |{' '}
                        <span className="text-gray-500">Classes:</span>{' '}
                        {serviceInfo?.detector_classes?.join(', ') || '-'}
                      </div>
                    )}
                    {result.metadata?.detections_summary && (
                      <div>
                        <span className="text-gray-500">Detections summary:</span>{' '}
                        {result.metadata.detections_summary
                          .map((d) => `${d.frame_index}:${d.count}`)
                          .join(' , ')}
                      </div>
                    )}
                    {result.debug_artifacts && (
                      <div>
                        <span className="text-gray-500">Debug artifacts:</span>{' '}
                        {result.debug_artifacts.metadata ||
                          result.debug_artifacts.overlay_image ||
                          '-'}
                      </div>
                    )}

                    <div className="flex items-center gap-3 pt-2">
                      <button
                        onClick={handleCopyDebugReport}
                        className="px-3 py-1 rounded bg-gray-800 text-white hover:bg-gray-900"
                      >
                        Copy Debug Report
                      </button>
                      {result.debug_artifacts?.metadata && (
                        <span className="text-gray-500">
                          Debug metadata: {result.debug_artifacts.metadata}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        )}

        {/* Batch Upload Card */}
        {uploadMode === 'batch' && (
          <div className="bg-white rounded-lg shadow-md p-8">
            {/* File Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Multiple Images
              </label>
              <input
                type="file"
                accept="image/jpeg,image/jpg,image/png,image/webp"
                multiple
                onChange={handleBatchFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              <p className="mt-2 text-xs text-gray-500">
                Supported formats: JPG, PNG, WEBP | Select multiple images for batch processing
              </p>
            </div>

            {/* Thumbnails Preview Grid */}
            {selectedFiles.length > 0 && (
              <div className="mb-6">
                <p className="text-sm font-medium text-gray-700 mb-3">
                  Selected Images ({selectedFiles.length})
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-h-96 overflow-y-auto p-2 border border-gray-200 rounded-lg">
                  {filePreviews.map((preview, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={preview}
                        alt={`Preview ${index + 1}`}
                        className="w-full h-32 object-cover rounded-lg border border-gray-300"
                      />
                      <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 text-white text-xs p-1 rounded-b-lg truncate">
                        {selectedFiles[index].name}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={handleBatchAnalyze}
                disabled={selectedFiles.length === 0 || batchLoading}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition font-medium"
              >
                {batchLoading ? `Analyzing... (${selectedFiles.length} images)` : 'Analyze Batch'}
              </button>
              <button
                onClick={handleClear}
                disabled={batchLoading}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:cursor-not-allowed transition"
              >
                Clear
              </button>
            </div>

            {/* Loading State */}
            {batchLoading && (
              <div className="mt-6 text-center">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-gray-600">
                  Processing {selectedFiles.length} images...
                </p>
              </div>
            )}

            {/* Error Display */}
            {batchError && (
              <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 font-medium">Error</p>
                <p className="text-sm text-red-600 mt-1">{batchError}</p>
              </div>
            )}

            {/* Batch Result Display */}
            {batchResult && (
              <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Batch Analysis Complete
                  </h3>
                  {batchResult.internal_batch_id && (
                    <Link
                      href={`/batches/${batchResult.internal_batch_id}`}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
                    >
                      View Batch Details
                    </Link>
                  )}
                </div>

                <div className="mb-4">
                  <p className="text-sm text-gray-500">Batch ID</p>
                  <p className="font-mono text-sm text-gray-900">{batchResult.batch_id}</p>
                </div>

                {/* Status Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      <p className="text-xs text-gray-500">EMPTY</p>
                    </div>
                    <p className="text-2xl font-bold text-green-600">
                      {batchResult.status_counts.EMPTY}
                    </p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                      <p className="text-xs text-gray-500">HALF</p>
                    </div>
                    <p className="text-2xl font-bold text-orange-600">
                      {batchResult.status_counts.HALF}
                    </p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <p className="text-xs text-gray-500">FULL</p>
                    </div>
                    <p className="text-2xl font-bold text-red-600">
                      {batchResult.status_counts.FULL}
                    </p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                      <p className="text-xs text-gray-500">NO BIN</p>
                    </div>
                    <p className="text-2xl font-bold text-gray-600">
                      {batchResult.status_counts.NO_BIN_DETECTED}
                    </p>
                  </div>
                </div>

                {/* Items Summary Table */}
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-100 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">File</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Status</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Confidence</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Bins</th>
                      </tr>
                    </thead>
                    <tbody>
                      {batchResult.items.map((item, index) => (
                        <tr key={item.id} className="border-b border-gray-200">
                          <td className="px-4 py-2 font-mono text-xs truncate max-w-xs">
                            {item.filename}
                          </td>
                          <td className="px-4 py-2">
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
                          <td className="px-4 py-2">{(item.confidence * 100).toFixed(0)}%</td>
                          <td className="px-4 py-2">{item.bins_detected}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Info Card */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            How it works
          </h3>
          <ul className="text-sm text-blue-800 space-y-2">
            {uploadMode === 'single' ? (
              <>
                <li>
                  • <strong>Video:</strong> Analyzes frames to detect bins and estimate fill levels
                </li>
                <li>
                  • <strong>Image:</strong> Detects bins in single frame and classifies fill level
                </li>
                <li>
                  • <strong>Result:</strong> Returns overall status (EMPTY/HALF/FULL) with confidence
                </li>
              </>
            ) : (
              <>
                <li>
                  • <strong>Batch Upload:</strong> Process multiple images simultaneously
                </li>
                <li>
                  • <strong>Analysis:</strong> Each image is analyzed independently for bin detection and fill level
                </li>
                <li>
                  • <strong>Summary:</strong> View aggregated results and individual item details
                </li>
                <li>
                  • <strong>Efficiency:</strong> Upload up to hundreds of images at once
                </li>
              </>
            )}
            <li>
              • <strong>Note:</strong> Uses mock classifier for MVP - train with real data for production
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
}
