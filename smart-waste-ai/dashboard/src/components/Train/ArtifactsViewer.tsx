"use client";

import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api/v1";
const API_ORIGIN = "http://localhost:8000";

interface ArtifactsResponse {
  artifacts: Record<string, string | null>;
  downloads: Record<string, string | null>;
}

export default function ArtifactsViewer() {
  const [data, setData] = useState<ArtifactsResponse | null>(null);

  const fetchArtifacts = async () => {
    const res = await fetch(`${API_BASE}/train/artifacts`);
    const json = await res.json();
    setData(json);
  };

  useEffect(() => {
    fetchArtifacts();
    const interval = setInterval(fetchArtifacts, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Debug/Artifacts</h2>
          <p className="text-sm text-gray-500">Training outputs and files</p>
        </div>
      </div>

      <div className="space-y-2 text-sm text-gray-700">
        <div>
          <span className="text-gray-500">best.pt:</span>{" "}
          {data?.artifacts?.best_pt || "-"}
        </div>
        <div>
          <span className="text-gray-500">results.png:</span>{" "}
          {data?.artifacts?.results_png || "-"}
        </div>
        <div>
          <span className="text-gray-500">confusion_matrix.png:</span>{" "}
          {data?.artifacts?.confusion_matrix_png || "-"}
        </div>
        <div>
          <span className="text-gray-500">metrics.json:</span>{" "}
          {data?.artifacts?.metrics_json || "-"}
        </div>
      </div>

      <div className="mt-4 flex gap-3">
        {data?.downloads?.best_pt && (
          <a
            href={`${API_ORIGIN}${data.downloads.best_pt}`}
            className="px-3 py-2 rounded bg-gray-800 text-white hover:bg-gray-900"
          >
            Download best.pt
          </a>
        )}
        {data?.downloads?.results_png && (
          <a
            href={`${API_ORIGIN}${data.downloads.results_png}`}
            className="px-3 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
          >
            results.png
          </a>
        )}
        {data?.downloads?.confusion_matrix_png && (
          <a
            href={`${API_ORIGIN}${data.downloads.confusion_matrix_png}`}
            className="px-3 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
          >
            confusion_matrix.png
          </a>
        )}
        {data?.downloads?.metrics_json && (
          <a
            href={`${API_ORIGIN}${data.downloads.metrics_json}`}
            className="px-3 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
          >
            metrics.json
          </a>
        )}
      </div>
    </div>
  );
}
