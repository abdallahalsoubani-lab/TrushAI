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
  capture_id?: number;
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

type Area = {
  id: number;
  name: string;
};

export default function WalkScanPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const inflightRef = useRef<boolean>(false);
  const frameCounterRef = useRef<number>(0);
  const tracksRef = useRef<Map<number, Track>>(new Map());
  const trackMetaRef = useRef<Map<number, { hits: number; lastSeen: number; lastCapture: number }>>(new Map());
  const nextIdRef = useRef<number>(1);
  const activeAreaIdRef = useRef<number | null>(null);

  const [running, setRunning] = useState(false);
  const [fps, setFps] = useState(6);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [captures, setCaptures] = useState<CaptureItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savedAreas, setSavedAreas] = useState<Area[]>([]);
  const [areaNameInput, setAreaNameInput] = useState<string>("");
  const [activeAreaId, setActiveAreaId] = useState<number | null>(null);
  const [activeAreaName, setActiveAreaName] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => {
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
      return crypto.randomUUID();
    }
    return `session_${Date.now()}`;
  });
  const sessionIdRef = useRef<string>(sessionId);
  const [minConf, setMinConf] = useState(() => {
    if (typeof window === "undefined") return 0.25;
    const stored = window.localStorage.getItem("walkscan_minConf");
    const value = stored ? Number(stored) : 0.25;
    return Number.isFinite(value) ? value : 0.25;
  });
  const [maxArea, setMaxArea] = useState(() => {
    if (typeof window === "undefined") return 0.85;
    const stored = window.localStorage.getItem("walkscan_maxArea");
    const value = stored ? Number(stored) : 0.85;
    return Number.isFinite(value) ? value : 0.85;
  });
  const [minArea, setMinArea] = useState(() => {
    if (typeof window === "undefined") return 0.03;
    const stored = window.localStorage.getItem("walkscan_minArea");
    const value = stored ? Number(stored) : 0.03;
    return Number.isFinite(value) ? value : 0.03;
  });
  const [minStableHits, setMinStableHits] = useState(() => {
    if (typeof window === "undefined") return 3;
    const stored = window.localStorage.getItem("walkscan_minStableHits");
    const value = stored ? Number(stored) : 3;
    return Number.isFinite(value) ? value : 3;
  });
  const [imgsz, setImgsz] = useState(() => {
    if (typeof window === "undefined") return 640;
    const stored = window.localStorage.getItem("walkscan_imgsz");
    const value = stored ? Number(stored) : 640;
    return Number.isFinite(value) ? value : 640;
  });
  const [processEveryNFrames, setProcessEveryNFrames] = useState(1);
  const [minAspect, setMinAspect] = useState(0.3);
  const [maxAspect, setMaxAspect] = useState(3.5);
  const [edgeMargin, setEdgeMargin] = useState(0.02);
  const [captureCooldownSec, setCaptureCooldownSec] = useState(4);
  const [lastApiInfo, setLastApiInfo] = useState<{
    binsDetected: number;
    latencyMs: number;
    areaId: number | null;
    status: string;
    detections: number;
  } | null>(null);
  const [noDetectionsCount, setNoDetectionsCount] = useState(0);

  const noDetectionsThreshold = 5;

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
        trackMeta.set(bestId, { hits, lastSeen: now, lastCapture: meta?.lastCapture ?? 0 });
        updated.push({ ...det, track_id: bestId });
      } else {
        const newId = nextIdRef.current++;
        used.add(newId);
        tracks.set(newId, { id: newId, bbox: det.bbox, lastSeen: Date.now() });
        trackMeta.set(newId, { hits: 1, lastSeen: now, lastCapture: 0 });
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
      if (ar < minAspect || ar > maxAspect) return false;
      let edges = 0;
      if (x1 < edgeMargin) edges += 1;
      if (y1 < edgeMargin) edges += 1;
      if (x2 > 1 - edgeMargin) edges += 1;
      if (y2 > 1 - edgeMargin) edges += 1;
      if (edges >= 2) return false;
      return true;
    });
  };

  const generateSessionId = () => {
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
      return crypto.randomUUID();
    }
    return `session_${Date.now()}`;
  };

  const applyActiveArea = (area: Area) => {
    setActiveAreaId(area.id);
    setActiveAreaName(area.name);
    setAreaNameInput(area.name);
    activeAreaIdRef.current = area.id;
  };

  const createOrGetArea = async (name: string) => {
    const res = await fetch(`${API_BASE}/api/v1/areas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => null);
      const detail = payload?.detail || "Failed to create area";
      throw new Error(detail);
    }
    return (await res.json()) as Area;
  };

  const ensureActiveArea = async () => {
    if (activeAreaIdRef.current) return;
    const name = areaNameInput.trim();
    if (!name) {
      throw new Error("Area name is required");
    }
    const area = await createOrGetArea(name);
    applyActiveArea(area);
    setSavedAreas((prev) => {
      if (prev.find((a) => a.id === area.id)) return prev;
      return [...prev, area].sort((a, b) => a.name.localeCompare(b.name));
    });
  };

  const setArea = async () => {
    const name = areaNameInput.trim();
    if (!name) {
      setError("Area name is required");
      return;
    }
    try {
      const area = await createOrGetArea(name);
      applyActiveArea(area);
      setSavedAreas((prev) => {
        if (prev.find((a) => a.id === area.id)) return prev;
        return [...prev, area].sort((a, b) => a.name.localeCompare(b.name));
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set area");
    }
  };

  const startNewSession = () => {
    const newId = generateSessionId();
    setSessionId(newId);
    sessionIdRef.current = newId;
    clearCaptures();
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
    frameCounterRef.current += 1;
    if (processEveryNFrames > 1 && frameCounterRef.current % processEveryNFrames !== 0) {
      return;
    }
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) return;
    inflightRef.current = true;
    setError(null);

    const offscreen = offscreenRef.current || document.createElement("canvas");
    offscreenRef.current = offscreen;
    const targetWidth = Math.min(video.videoWidth, imgsz);
    const scale = targetWidth / video.videoWidth;
    const targetHeight = Math.max(1, Math.round(video.videoHeight * scale));
    offscreen.width = targetWidth;
    offscreen.height = targetHeight;
    const ctx = offscreen.getContext("2d");
    if (!ctx) {
      inflightRef.current = false;
      return;
    }
    ctx.drawImage(video, 0, 0, targetWidth, targetHeight);

    const blob = await new Promise<Blob | null>((resolve) => {
      offscreen.toBlob((b) => resolve(b), "image/jpeg", 0.8);
    });
    if (!blob) {
      inflightRef.current = false;
      return;
    }

    try {
      const currentAreaId = activeAreaIdRef.current;
      const currentSessionId = sessionIdRef.current;
      if (!currentAreaId) {
        throw new Error("Set an area before scanning");
      }
      const formData = new FormData();
      formData.append("file", blob, "frame.jpg");
      const query = new URLSearchParams({
        session_id: currentSessionId,
        area_id: String(currentAreaId),
        imgsz: String(imgsz),
        conf: String(minConf),
      });
      const start = performance.now();
      const res = await fetch(`${API_BASE}/api/v1/analyze-frame?${query.toString()}`, {
        method: "POST",
        body: formData,
      });
      const elapsed = performance.now() - start;
      if (!res.ok) {
        throw new Error("Analyze frame failed");
      }
      const data = await res.json();
      const rawDetections = Array.isArray(data.detections) ? data.detections : [];
      const detectionsCount = rawDetections.length;
      setLastApiInfo({
        binsDetected: Number(data.bins_detected || 0),
        latencyMs: Math.round(elapsed),
        areaId: currentAreaId,
        status: String(data.status || "UNKNOWN"),
        detections: detectionsCount,
      });
      setNoDetectionsCount((prev) => (detectionsCount === 0 ? prev + 1 : 0));
      const filtered = filterDetections(rawDetections);
      const tracked = assignTrackIds(filtered, fps);
      setDetections(tracked);
      drawOverlay(tracked);

      const thumbnail = offscreen.toDataURL("image/jpeg", 0.6);
      const newCaptures: CaptureItem[] = [];
      for (const det of tracked) {
        if (!det.track_id) continue;
        const meta = trackMetaRef.current.get(det.track_id);
        if (!meta || meta.hits < minStableHits) continue;
        const now = Date.now();
        if (meta.lastCapture && now - meta.lastCapture < captureCooldownSec * 1000) {
          continue;
        }
        let captureId: number | undefined;
        try {
          const captureForm = new FormData();
          captureForm.append("file", blob, `capture_${det.track_id}.jpg`);
          captureForm.append("area_id", String(currentAreaId));
          captureForm.append("session_id", currentSessionId);
          captureForm.append("track_id", det.track_id.toString());
          captureForm.append("status", det.fill_status);
          captureForm.append("confidence", det.fill_conf.toString());
          captureForm.append("detections_json", JSON.stringify(det));

          const captureRes = await fetch(`${API_BASE}/api/v1/walkscan/capture`, {
            method: "POST",
            body: captureForm,
          });
          if (captureRes.ok) {
            const captureData = await captureRes.json();
            captureId = captureData.capture_id;
            trackMetaRef.current.set(det.track_id, {
              hits: meta.hits,
              lastSeen: meta.lastSeen,
              lastCapture: now,
            });
          }
        } catch {
          // Ignore capture storage errors, keep local capture
        }
        newCaptures.push({
          id: det.track_id,
          capture_id: captureId,
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
      await ensureActiveArea();
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
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera permission denied");
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
    setNoDetectionsCount(0);
  };

  const clearCaptures = () => {
    setCaptures([]);
    setDetections([]);
    tracksRef.current.clear();
    trackMetaRef.current.clear();
    nextIdRef.current = 1;
    frameCounterRef.current = 0;
    drawOverlay([]);
    setNoDetectionsCount(0);
    setLastApiInfo(null);
  };

  const exportJson = () => {
    const exportData = captures.map((c) => ({
      id: c.id,
      capture_id: c.capture_id,
      timestamp: c.timestamp,
      fill_status: c.fill_status,
      conf: c.conf,
      bbox: c.bbox,
      area_id: activeAreaId,
      area_name: activeAreaName,
      session_id: sessionId,
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
  }, [
    running,
    fps,
    processEveryNFrames,
    minConf,
    minArea,
    maxArea,
    minStableHits,
    imgsz,
    minAspect,
    maxAspect,
    edgeMargin,
    captureCooldownSec,
  ]);

  useEffect(() => {
    const loadAreas = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/areas`);
        if (!res.ok) return;
        const data = await res.json();
        const list = (data.areas || []) as Area[];
        setSavedAreas(list);
      } catch {
        // Ignore area fetch errors
      }
    };
    loadAreas();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("walkscan_minConf", String(minConf));
  }, [minConf]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("walkscan_maxArea", String(maxArea));
  }, [maxArea]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("walkscan_minArea", String(minArea));
  }, [minArea]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("walkscan_minStableHits", String(minStableHits));
  }, [minStableHits]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("walkscan_imgsz", String(imgsz));
  }, [imgsz]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    activeAreaIdRef.current = activeAreaId;
  }, [activeAreaId]);

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
            <div className="mb-4 rounded-lg border bg-gray-50 p-3 text-xs text-gray-600 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  placeholder="Area name"
                  value={areaNameInput}
                  onChange={(e) => setAreaNameInput(e.target.value)}
                  className="flex-1 min-w-[180px] border rounded px-2 py-1"
                />
                <button
                  onClick={setArea}
                  className="px-3 py-1 rounded bg-gray-800 text-white hover:bg-gray-900"
                >
                  Set Area
                </button>
                <button
                  onClick={async () => {
                    const name = areaNameInput.trim();
                    if (!name) {
                      setError("Area name is required");
                      return;
                    }
                    try {
                      const area = await createOrGetArea(name);
                      applyActiveArea(area);
                      setSavedAreas((prev) => {
                        if (prev.find((a) => a.id === area.id)) return prev;
                        return [...prev, area].sort((a, b) => a.name.localeCompare(b.name));
                      });
                      startNewSession();
                      setAreaNameInput("");
                      setError(null);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Failed to set area");
                    }
                  }}
                  className="px-3 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
                >
                  + New Area
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span>Saved Areas</span>
                <select
                  value={activeAreaId ?? ""}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    const selected = savedAreas.find((a) => a.id === id) || null;
                    if (selected) {
                      applyActiveArea(selected);
                      startNewSession();
                    } else {
                      setActiveAreaId(null);
                      setActiveAreaName(null);
                      setAreaNameInput("");
                      activeAreaIdRef.current = null;
                      startNewSession();
                    }
                  }}
                  className="border rounded px-2 py-1"
                >
                  <option value="">Select</option>
                  {savedAreas.map((area) => (
                    <option key={area.id} value={area.id}>
                      {area.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                Active area:{" "}
                <span className="font-semibold">{activeAreaName ?? "Not set"}</span>
              </div>
              <div>
                Session ID: <span className="font-mono">{sessionId}</span>
              </div>
            </div>
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden">
              <video
                ref={videoRef}
                onLoadedMetadata={syncCanvas}
                className="absolute inset-0 w-full h-full object-cover"
              />
              <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
            </div>
            <div className="mt-2 text-xs text-gray-600">
              Last API:{" "}
              {lastApiInfo
                ? `status=${lastApiInfo.status} detections=${lastApiInfo.detections} bins_detected=${lastApiInfo.binsDetected} latency=${lastApiInfo.latencyMs}ms area_id=${lastApiInfo.areaId}`
                : "No requests yet"}
            </div>
            {noDetectionsCount >= noDetectionsThreshold && (
              <div className="mt-1 text-xs text-amber-700">
                No detections for {noDetectionsCount} cycles. Check conf/imgsz.
              </div>
            )}
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
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span>Every N</span>
                <select
                  value={processEveryNFrames}
                  onChange={(e) => setProcessEveryNFrames(Number(e.target.value))}
                  className="border rounded px-2 py-1"
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                </select>
              </div>
            </div>
            <div className="mt-4 text-xs text-gray-600">
              <div className="font-semibold mb-2">Filters</div>
              <div className="grid grid-cols-2 md:grid-cols-7 gap-3">
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
                  <span>Quality</span>
                  <select
                    value={imgsz}
                    onChange={(e) => setImgsz(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  >
                    <option value={320}>Fast</option>
                    <option value={480}>Balanced</option>
                    <option value={640}>Accurate</option>
                  </select>
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
                  <span>minAR</span>
                  <input
                    type="number"
                    step="0.1"
                    value={minAspect}
                    onChange={(e) => setMinAspect(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span>maxAR</span>
                  <input
                    type="number"
                    step="0.1"
                    value={maxAspect}
                    onChange={(e) => setMaxAspect(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span>edgeMargin</span>
                  <input
                    type="number"
                    step="0.01"
                    value={edgeMargin}
                    onChange={(e) => setEdgeMargin(Number(e.target.value))}
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
                <label className="flex flex-col gap-1">
                  <span>cooldown(s)</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={captureCooldownSec}
                    onChange={(e) => setCaptureCooldownSec(Number(e.target.value))}
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
