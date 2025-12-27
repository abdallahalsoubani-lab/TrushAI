"use client";

import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api/v1";

interface TrainStatus {
  state: "idle" | "running" | "completed" | "failed";
  epoch: number;
  epochs: number;
  metrics: {
    loss?: number;
    map50?: number;
    map5095?: number;
  };
  logs_tail: string;
  artifacts: Record<string, string | null>;
  error?: string | null;
  project_name?: string;
  device?: string;
}

interface TrainingPanelProps {
  datasetReady: boolean;
  datasetYamlPath: string | null;
}

export default function TrainingPanel({ datasetReady, datasetYamlPath }: TrainingPanelProps) {
  const [modelSize, setModelSize] = useState("n");
  const [epochs, setEpochs] = useState(50);
  const [imgsz, setImgsz] = useState(640);
  const [batch, setBatch] = useState(8);
  const [device, setDevice] = useState("auto");
  const [projectName, setProjectName] = useState("trashbin-train");
  const [status, setStatus] = useState<TrainStatus>({
    state: "idle",
    epoch: 0,
    epochs: 0,
    metrics: {},
    logs_tail: "",
    artifacts: {},
  });
  const [message, setMessage] = useState<string | null>(null);
  const [deploying, setDeploying] = useState(false);

  const fetchStatus = async () => {
    const res = await fetch(`${API_BASE}/train/status`);
    const data = await res.json();
    setStatus(data);
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setMessage(null);
    if (!datasetReady || !datasetYamlPath) {
      setMessage("Prepare the dataset first.");
      return;
    }
    const res = await fetch(`${API_BASE}/train/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_size: modelSize,
        epochs,
        imgsz,
        batch,
        device,
        project_name: projectName,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Failed to start training");
      return;
    }
    setMessage("Training started");
  };

  const handleDeployBest = async () => {
    if (!status.artifacts.best_pt) return;
    setDeploying(true);
    setMessage(null);
    const res = await fetch(`${API_BASE}/training/deploy-best`, {
      method: "POST",
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || "Failed to deploy model");
      setDeploying(false);
      return;
    }
    const target = data.to || "backend/weights/bins.pt";
    setMessage(`Model deployed to ${target}`);
    setDeploying(false);
  };

  const progress = status.epochs > 0 ? Math.round((status.epoch / status.epochs) * 100) : 0;

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Training Panel</h2>
          <p className="text-sm text-gray-500">Start training and monitor progress</p>
        </div>
        <span className="text-sm text-gray-600">State: {status.state}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="text-xs text-gray-500">Model Size</label>
          <select
            value={modelSize}
            onChange={(e) => setModelSize(e.target.value)}
            className="w-full border rounded px-2 py-1"
          >
            <option value="n">n</option>
            <option value="s">s</option>
            <option value="m">m</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Epochs</label>
          <input
            type="number"
            value={epochs}
            onChange={(e) => setEpochs(Number(e.target.value))}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">Image Size</label>
          <input
            type="number"
            value={imgsz}
            onChange={(e) => setImgsz(Number(e.target.value))}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">Batch</label>
          <input
            type="number"
            value={batch}
            onChange={(e) => setBatch(Number(e.target.value))}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">Device</label>
          <select
            value={device}
            onChange={(e) => setDevice(e.target.value)}
            className="w-full border rounded px-2 py-1"
          >
            <option value="auto">Auto</option>
            <option value="mps">MPS</option>
            <option value="cpu">CPU</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Project Name</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full border rounded px-2 py-1"
          />
        </div>
      </div>

      <button
        onClick={handleStart}
        disabled={!datasetReady || status.state === "running"}
        className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300"
      >
        Start Training
      </button>

      {message && <p className="mt-2 text-sm text-gray-600">{message}</p>}

      <div className="mt-4">
        <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
          <span>
            Epoch {status.epoch} / {status.epochs}
          </span>
          <span>{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <p className="text-gray-500">Loss</p>
          <p className="font-medium">{status.metrics?.loss ?? "-"}</p>
        </div>
        <div>
          <p className="text-gray-500">mAP50</p>
          <p className="font-medium">{status.metrics?.map50 ?? "-"}</p>
        </div>
        <div>
          <p className="text-gray-500">mAP50-95</p>
          <p className="font-medium">{status.metrics?.map5095 ?? "-"}</p>
        </div>
        <div>
          <p className="text-gray-500">Device</p>
          <p className="font-medium">{status.device ?? "-"}</p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-sm text-gray-500 mb-2">Logs (tail)</p>
        <pre className="bg-gray-900 text-green-200 text-xs p-3 rounded h-48 overflow-y-auto whitespace-pre-wrap">
          {status.logs_tail || "No logs yet"}
        </pre>
      </div>

      {status.state === "completed" && status.artifacts?.best_pt && (
        <div className="mt-4 flex items-center gap-3">
          <a
            href={`${API_BASE}/train/download/best`}
            className="px-4 py-2 rounded bg-gray-800 text-white hover:bg-gray-900"
          >
            Download best.pt
          </a>
          <button
            onClick={handleDeployBest}
            disabled={deploying}
            className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-300"
          >
            {deploying ? "Deploying..." : "Deploy best.pt"}
          </button>
        </div>
      )}

      {status.state === "failed" && (
        <div className="mt-4 text-sm text-red-600">
          Training failed: {status.error}
        </div>
      )}
    </div>
  );
}
