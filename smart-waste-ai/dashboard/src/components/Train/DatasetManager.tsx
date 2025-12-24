"use client";

import { useEffect, useState } from "react";
import AnnotationModal from "./AnnotationModal";

const API_BASE = "http://localhost:8000/api/v1";
const PAGE_SIZE = 12;

interface ImageItem {
  filename: string;
  path: string;
  annotated: boolean;
}

interface DatasetInfo {
  ok: boolean;
  trainCount: number;
  valCount: number;
  datasetYamlPath: string;
}

interface DatasetManagerProps {
  onPrepared: (info: DatasetInfo | null) => void;
}

export default function DatasetManager({ onPrepared }: DatasetManagerProps) {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<ImageItem | null>(null);
  const [prepareInfo, setPrepareInfo] = useState<string | null>(null);
  const [prepareError, setPrepareError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(images.length / PAGE_SIZE));
  const pageImages = images.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const fetchImages = async () => {
    const res = await fetch(`${API_BASE}/dataset/list`);
    const data = await res.json();
    setImages(data.images || []);
  };

  useEffect(() => {
    fetchImages();
  }, []);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setLoading(true);
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append("images", file));
    await fetch(`${API_BASE}/dataset/upload`, {
      method: "POST",
      body: formData,
    });
    await fetchImages();
    setLoading(false);
  };

  const handleSaveAnnotation = async (bbox: { x: number; y: number; w: number; h: number }) => {
    if (!selected) return;
    await fetch(`${API_BASE}/dataset/annotate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: selected.filename, bbox }),
    });
    setSelected(null);
    await fetchImages();
  };

  const handlePrepare = async () => {
    setPrepareInfo(null);
    setPrepareError(null);
    const res = await fetch(`${API_BASE}/dataset/prepare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ train_ratio: 0.8 }),
    });
    const data = await res.json();
    if (!res.ok) {
      setPrepareError(data.detail || "Failed to prepare dataset");
      onPrepared(null);
      return;
    }
    setPrepareInfo(
      `Prepared dataset: train=${data.trainCount}, val=${data.valCount}`
    );
    onPrepared(data);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Dataset Manager</h2>
          <p className="text-sm text-gray-500">Upload and annotate images</p>
        </div>
        <label className="px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700">
          Upload Images
          <input
            type="file"
            multiple
            accept="image/jpeg,image/jpg,image/png"
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
          />
        </label>
      </div>

      {loading && <p className="text-sm text-gray-600 mb-4">Uploading...</p>}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {pageImages.map((img) => (
          <div key={img.filename} className="border rounded-lg p-2 bg-gray-50">
            <img
              src={`${API_BASE}/dataset/image/${img.filename}`}
              alt={img.filename}
              className="w-full h-32 object-cover rounded"
            />
            <div className="mt-2 flex items-center justify-between">
              <span className={`text-xs ${img.annotated ? "text-green-600" : "text-red-600"}`}>
                {img.annotated ? "Annotated ✅" : "Not Annotated ❌"}
              </span>
              <button
                onClick={() => setSelected(img)}
                className="text-xs px-2 py-1 rounded bg-gray-200 hover:bg-gray-300"
              >
                Annotate
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between mt-4">
        <div className="text-sm text-gray-600">
          Page {page} / {totalPages}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300"
          >
            Prev
          </button>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300"
          >
            Next
          </button>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-4">
        <button
          onClick={handlePrepare}
          className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700"
        >
          Auto split train/val (80/20)
        </button>
        {prepareInfo && <span className="text-sm text-gray-600">{prepareInfo}</span>}
        {prepareError && <span className="text-sm text-red-600">{prepareError}</span>}
      </div>

      {selected && (
        <AnnotationModal
          imageUrl={`${API_BASE}/dataset/image/${selected.filename}`}
          filename={selected.filename}
          onClose={() => setSelected(null)}
          onSave={handleSaveAnnotation}
        />
      )}
    </div>
  );
}
