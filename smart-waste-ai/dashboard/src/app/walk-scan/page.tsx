"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import "../globals.css";

const API_BASE = "http://localhost:8000";

type Detection = {
  bbox: [number, number, number, number];
  conf: number;
  label: string;
  fill_status: "EMPTY" | "HALF" | "FULL";
  fill_conf: number;
  track_id?: number | null;
};

type CaptureItem = {
  id: number;
  timestamp: string;
  fill_status: string;
  conf: number;
  bbox: [number, number, number, number];
  thumbnail?: string;
};

type Track = {
  id: number;
  bbox: [number, number, number, number];
  lastSeen: number;
};

export default function WalkScanPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const inflightRef = useRef<boolean>(false);
  const tracksRef = useRef<Map<number, Track>>(new Map());
  const trackMetaRef = useRef<Map<number, { hits: number; lastSeen: number }>>(new Map());
  const nextIdRef = useRef<number>(1);
  const capturedIdsRef = useRef<Set<number>>(new Set());

  const [running, setRunning] = useState(false);
  const [fps, setFps] = useState(2);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [captures, setCaptures] = useState<CaptureItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [minConf, setMinConf] = useState(0.25);
  const [maxArea, setMaxArea] = useState(0.85);
  const [minArea, setMinArea] = useState(0.02);
  const [minStableHits, setMinStableHits] = useState(2);

  const syncCanvas = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  };

  const iou = (a: [number, number, number, number], b: [number, number, number, number]) => {
    const x1 = Math.max(a[0], b[0]);
    const y1 = Math.max(a[1], b[1]);
    const x2 = Math.min(a[2], b[2]);
    const y2 = Math.min(a[3], b[3]);
    const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    const areaA = Math.max(0, a[2] - a[0]) * Math.max(0, a[3] - a[1]);
    const areaB = Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);
    const union = areaA + areaB - inter;
    return union > 0 ? inter / union : 0;
  };

  const assignTrackIds = (items: Detection[], fpsValue: number): Detection[] => {
    const tracks = tracksRef.current;
    const trackMeta = trackMetaRef.current;
    const used = new Set<number>();
    const updated: Detection[] = [];
    const now = Date.now();
    const windowMs = Math.max(1000, Math.round((1000 / fpsValue) * 2.5));

    for (const det of items) {
      let bestId: number | null = null;
      let bestIou = 0;
      for (const track of tracks.values()) {
        if (used.has(track.id)) continue;
        const score = iou(det.bbox, track.bbox);
        if (score > bestIou) {
          bestIou = score;
          bestId = track.id;
        }
      }
      if (bestIou >= 0.3 && bestId !== null) {
        used.add(bestId);
        tracks.set(bestId, { id: bestId, bbox: det.bbox, lastSeen: Date.now() });
        const meta = trackMeta.get(bestId);
        const hits = meta && now - meta.lastSeen <= windowMs ? meta.hits + 1 : 1;
        trackMeta.set(bestId, { hits, lastSeen: now });
        updated.push({ ...det, track_id: bestId });
      } else {
        const newId = nextIdRef.current++;
        used.add(newId);
        tracks.set(newId, { id: newId, bbox: det.bbox, lastSeen: Date.now() });
        trackMeta.set(newId, { hits: 1, lastSeen: now });
        updated.push({ ...det, track_id: newId });
      }
    }

    for (const [id, track] of tracks.entries()) {
      if (Date.now() - track.lastSeen > 5000) {
        tracks.delete(id);
        trackMeta.delete(id);
      }
    }

    return updated;
  };

  const filterDetections = (items: Detection[]) => {
    return items.filter((det) => {
      if (det.label !== "trash_container") return false;
      if (det.conf < minConf) return false;
      const [x1, y1, x2, y2] = det.bbox;
      const w = Math.max(0, x2 - x1);
      const h = Math.max(0, y2 - y1);
      const area = w * h;
      if (area > maxArea || area < minArea) return false;
      if (h === 0) return false;
      const ar = w / h;
      if (ar < 0.3 || ar > 2.2) return false;
      let edges = 0;
      if (x1 < 0.01) edges += 1;
      if (y1 < 0.01) edges += 1;
      if (x2 > 0.99) edges += 1;
      if (y2 > 0.99) edges += 1;
      if (edges >= 3) return false;
      return true;
    });
  };

  const drawOverlay = (items: Detection[]) => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    syncCanvas();
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#22c55e";
    ctx.fillStyle = "#22c55e";
    ctx.lineWidth = 2;
    ctx.font = "14px sans-serif";

    for (const det of items) {
      const [x1, y1, x2, y2] = det.bbox;
      const px1 = x1 * canvas.width;
      const py1 = y1 * canvas.height;
      const pw = (x2 - x1) * canvas.width;
      const ph = (y2 - y1) * canvas.height;
      ctx.strokeRect(px1, py1, pw, ph);
      const label = `ID ${det.track_id ?? "-"} ${det.fill_status} ${(det.fill_conf * 100).toFixed(0)}%`;
      ctx.fillText(label, px1, Math.max(12, py1 - 6));
    }
  };

  const captureFrame = async () => {
    if (inflightRef.current) return;
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) return;
    inflightRef.current = true;
    setError(null);

    const offscreen = offscreenRef.current || document.createElement("canvas");
    offscreenRef.current = offscreen;
    offscreen.width = video.videoWidth;
    offscreen.height = video.videoHeight;
    const ctx = offscreen.getContext("2d");
    if (!ctx) {
      inflightRef.current = false;
      return;
    }
    ctx.drawImage(video, 0, 0);

    const blob = await new Promise<Blob | null>((resolve) => {
      offscreen.toBlob((b) => resolve(b), "image/jpeg", 0.8);
    });
    if (!blob) {
      inflightRef.current = false;
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", blob, "frame.jpg");
      const res = await fetch(`${API_BASE}/api/v1/analyze-frame`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error("Analyze frame failed");
      }
      const data = await res.json();
      const filtered = filterDetections(data.detections || []);
      const tracked = assignTrackIds(filtered, fps);
      setDetections(tracked);
      drawOverlay(tracked);

      const thumbnail = offscreen.toDataURL("image/jpeg", 0.6);
      const newCaptures: CaptureItem[] = [];
      for (const det of tracked) {
        if (!det.track_id || capturedIdsRef.current.has(det.track_id)) continue;
        const meta = trackMetaRef.current.get(det.track_id);
        if (!meta || meta.hits < minStableHits) continue;
        capturedIdsRef.current.add(det.track_id);
        newCaptures.push({
          id: det.track_id,
          timestamp: new Date().toISOString(),
          fill_status: det.fill_status,
          conf: det.fill_conf,
          bbox: det.bbox,
          thumbnail,
        });
      }
      if (newCaptures.length) {
        setCaptures((prev) => [...newCaptures, ...prev]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze frame");
    } finally {
      inflightRef.current = false;
    }
  };

  const startScan = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      syncCanvas();
      setRunning(true);
    } catch (err) {
      setError("Camera permission denied");
    }
  };

  const stopScan = () => {
    setRunning(false);
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setDetections([]);
    drawOverlay([]);
  };

  const clearCaptures = () => {
    setCaptures([]);
    capturedIdsRef.current.clear();
    tracksRef.current.clear();
    trackMetaRef.current.clear();
    nextIdRef.current = 1;
  };

  const exportJson = () => {
    const exportData = captures.map((c) => ({
      id: c.id,
      timestamp: c.timestamp,
      fill_status: c.fill_status,
      conf: c.conf,
      bbox: c.bbox,
    }));
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `walk_scan_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    if (!running) return;
    const interval = window.setInterval(captureFrame, Math.max(200, 1000 / fps));
    intervalRef.current = interval;
    return () => {
      window.clearInterval(interval);
    };
  }, [running, fps]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Live Camera Walk Scan</h1>
              <p className="text-sm text-gray-500 mt-1">
                Live bin detection and capture while walking
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden">
              <video
                ref={videoRef}
                onLoadedMetadata={syncCanvas}
                className="absolute inset-0 w-full h-full object-cover"
              />
              <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
            </div>
            <div className="mt-4 flex flex-wrap gap-3 items-center">
              {!running ? (
                <button
                  onClick={startScan}
                  className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700"
                >
                  Start
                </button>
              ) : (
                <button
                  onClick={stopScan}
                  className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700"
                >
                  Stop
                </button>
              )}
              <button
                onClick={clearCaptures}
                className="px-4 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
              >
                Clear
              </button>
              <button
                onClick={exportJson}
                className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
              >
                Export JSON
              </button>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span>FPS</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={fps}
                  onChange={(e) => setFps(Number(e.target.value))}
                  className="w-16 border rounded px-2 py-1"
                />
              </div>
            </div>
            <div className="mt-4 text-xs text-gray-600">
              <div className="font-semibold mb-2">Filters</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <label className="flex flex-col gap-1">
                  <span>minConf</span>
                  <input
                    type="number"
                    step="0.01"
                    value={minConf}
                    onChange={(e) => setMinConf(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span>maxArea</span>
                  <input
                    type="number"
                    step="0.01"
                    value={maxArea}
                    onChange={(e) => setMaxArea(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span>minArea</span>
                  <input
                    type="number"
                    step="0.01"
                    value={minArea}
                    onChange={(e) => setMinArea(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span>minStableHits</span>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={minStableHits}
                    onChange={(e) => setMinStableHits(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  />
                </label>
              </div>
            </div>
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          </div>

          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Captured Bins</h2>
              <span className="text-xs text-gray-500">{captures.length} items</span>
            </div>
            <div className="space-y-3 max-h-[520px] overflow-y-auto">
              {captures.length === 0 && (
                <p className="text-sm text-gray-500">No captures yet.</p>
              )}
              {captures.map((cap) => (
                <div key={cap.id} className="flex gap-3 border rounded-lg p-2">
                  {cap.thumbnail ? (
                    <img
                      src={cap.thumbnail}
                      alt={`Capture ${cap.id}`}
                      className="w-20 h-16 object-cover rounded"
                    />
                  ) : (
                    <div className="w-20 h-16 bg-gray-200 rounded" />
                  )}
                  <div className="text-xs text-gray-700">
                    <div className="font-semibold">ID {cap.id}</div>
                    <div>Status: {cap.fill_status}</div>
                    <div>Conf: {(cap.conf * 100).toFixed(0)}%</div>
                    <div>{new Date(cap.timestamp).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
