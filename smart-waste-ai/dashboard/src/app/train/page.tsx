"use client";

import { useState } from "react";
import "../globals.css";
import Link from "next/link";
import DatasetManager from "../../components/Train/DatasetManager";
import TrainingPanel from "../../components/Train/TrainingPanel";
import ArtifactsViewer from "../../components/Train/ArtifactsViewer";

export default function TrainPage() {
  const [datasetReady, setDatasetReady] = useState(false);
  const [datasetYamlPath, setDatasetYamlPath] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Model Training</h1>
              <p className="text-sm text-gray-500 mt-1">
                Upload, annotate, and train a trash container model
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

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <DatasetManager
          onPrepared={(info) => {
            setDatasetReady(!!info?.ok);
            setDatasetYamlPath(info?.datasetYamlPath || null);
          }}
        />
        <TrainingPanel datasetReady={datasetReady} datasetYamlPath={datasetYamlPath} />
        <ArtifactsViewer />
      </main>
    </div>
  );
}
