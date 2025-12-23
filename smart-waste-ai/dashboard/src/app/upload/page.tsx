"use client";

/**
 * Upload Page - File Upload and Analysis
 * =======================================
 * Allows users to upload video or image files for trash bin analysis.
 *
 * Features:
 * - File input for video (.mp4, .avi, .mov) or image (.jpg, .png)
 * - File preview (image preview or filename for video)
 * - Analyze button with loading state
 * - Result display with color-coded status
 * - Clear button to reset and upload another file
 *
 * TODO: Add drag-and-drop file upload
 * TODO: Add progress bar for upload
 * TODO: Add multiple file upload support
 * TODO: Display detected bins in image/video frame
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
}

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Upload & Analyze
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Upload a video or image to detect trash bin fill levels
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

      <main className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Upload Card */}
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
            </div>
          )}
        </div>

        {/* Info Card */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            How it works
          </h3>
          <ul className="text-sm text-blue-800 space-y-2">
            <li>
              • <strong>Video:</strong> Analyzes frames to detect bins and estimate fill levels
            </li>
            <li>
              • <strong>Image:</strong> Detects bins in single frame and classifies fill level
            </li>
            <li>
              • <strong>Result:</strong> Returns overall status (EMPTY/HALF/FULL) with confidence
            </li>
            <li>
              • <strong>Note:</strong> Uses mock classifier for MVP - train with real data for production
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
}
