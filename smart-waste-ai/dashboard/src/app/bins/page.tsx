"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import "../globals.css";

const API_BASE = "http://localhost:8000";

type Area = {
  id: number;
  name: string;
};

type BinItem = {
  id: number;
  bin_key: string;
  area: Area | null;
  last_status: string | null;
  last_conf: number | null;
  capture_count: number;
  ops_status: string;
  priority_score: number;
  last_seen_at: string | null;
  updated_at: string;
  thumbnail_url: string | null;
};

export default function BinsPage() {
  const [bins, setBins] = useState<BinItem[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [areaId, setAreaId] = useState<string>("");
  const [opsStatus, setOpsStatus] = useState<string>("");
  const [minPriority, setMinPriority] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const searchParams = useSearchParams();

  const formatOpsStatus = (value: string) => {
    if (value === "TRUCK_SENT") return "TRUCK_DISPATCHED";
    if (value === "CLOSED") return "FALSE_POSITIVE";
    return value;
  };

  const fetchAreas = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/areas`);
      if (!res.ok) return;
      const data = await res.json();
      setAreas(data.areas || []);
    } catch {
      // Ignore
    }
  };

  const fetchBins = async () => {
    try {
      const params = new URLSearchParams();
      if (areaId) params.set("area_id", areaId);
      if (opsStatus) params.set("ops_status", opsStatus);
      if (minPriority > 0) params.set("min_priority", String(minPriority));
      const res = await fetch(`${API_BASE}/api/v1/dashboard/bins?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to load bins");
      const data = await res.json();
      setBins(data.bins || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bins");
    }
  };

  const deleteBin = async (binId: number) => {
    if (!window.confirm("Delete this bin and all related captures?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/bins/${binId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete bin");
      setBins((prev) => prev.filter((b) => b.id !== binId));
      setToast("Bin deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete bin");
    }
  };

  useEffect(() => {
    fetchAreas();
  }, []);

  useEffect(() => {
    fetchBins();
  }, [areaId, opsStatus, minPriority]);

  useEffect(() => {
    const param = searchParams.get("area_id");
    if (param) {
      setAreaId(param);
    }
    const toastMsg = window.localStorage.getItem("bins_toast");
    if (toastMsg) {
      setToast(toastMsg);
      window.localStorage.removeItem("bins_toast");
    }
  }, [searchParams]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Bins</h1>
              <p className="text-sm text-gray-500 mt-1">
                Walk Scan bins by area with operational status
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
        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
        {toast && <p className="text-sm text-green-700 mb-4">{toast}</p>}
        <div className="bg-white rounded-lg shadow-md p-4 mb-4">
          <div className="flex flex-wrap gap-3 items-center text-sm">
            <div className="flex items-center gap-2">
              <span>Area</span>
              <select
                value={areaId}
                onChange={(e) => setAreaId(e.target.value)}
                className="border rounded px-2 py-1"
              >
                <option value="">All</option>
                {areas.map((area) => (
                  <option key={area.id} value={area.id}>
                    {area.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span>Status</span>
              <select
                value={opsStatus}
                onChange={(e) => setOpsStatus(e.target.value)}
                className="border rounded px-2 py-1"
              >
                <option value="">All</option>
                <option value="NEW">NEW</option>
                <option value="ON_PROCESS">ON_PROCESS</option>
                <option value="TRUCK_DISPATCHED">TRUCK_DISPATCHED</option>
                <option value="EMPTIED">EMPTIED</option>
                <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span>Min Priority</span>
              <input
                type="number"
                min={0}
                value={minPriority}
                onChange={(e) => setMinPriority(Number(e.target.value))}
                className="w-24 border rounded px-2 py-1"
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {bins.map((bin) => (
              <div key={bin.id} className="border rounded-lg p-3 hover:bg-gray-50 flex gap-3">
                <Link href={`/bins/${bin.id}`} className="flex gap-3 flex-1">
                  {bin.thumbnail_url ? (
                    <img
                      src={`${API_BASE}${bin.thumbnail_url}`}
                      alt={`Bin ${bin.id}`}
                      className="w-20 h-16 object-cover rounded"
                    />
                  ) : (
                    <div className="w-20 h-16 bg-gray-200 rounded" />
                  )}
                  <div className="text-xs text-gray-700 space-y-1">
                    <div className="font-semibold">Bin #{bin.id}</div>
                    <div>Area: {bin.area?.name || "Unknown"}</div>
                    <div>
                      Status: {bin.last_status || "-"} ({((bin.last_conf || 0) * 100).toFixed(0)}%)
                    </div>
                    <div>Ops: {formatOpsStatus(bin.ops_status)}</div>
                    <div>Priority: {bin.priority_score.toFixed(0)}</div>
                    <div>Captures: {bin.capture_count}</div>
                  </div>
                </Link>
                <div className="flex flex-col gap-2 text-xs">
                  <button
                    onClick={() => deleteBin(bin.id)}
                    className="px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
          {bins.length === 0 && (
            <p className="text-sm text-gray-500">No bins yet.</p>
          )}
        </div>
      </main>
    </div>
  );
}
