"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import "../../globals.css";

const API_BASE = "http://localhost:8000";

type DashboardArea = {
  area_id: number;
  area_name: string;
  bins_count: number;
  captures_count: number;
  max_priority: number;
  last_seen: string | null;
};

type BinItem = {
  id: number;
  bin_key: string;
  last_status: string | null;
  last_conf: number | null;
  capture_count: number;
  ops_status: string;
  priority_score: number;
  last_seen_at: string | null;
  thumbnail_url: string | null;
};

export default function AreaDetailPage({ params }: { params: { id: string } }) {
  const [area, setArea] = useState<DashboardArea | null>(null);
  const [bins, setBins] = useState<BinItem[]>([]);
  const [opsStatus, setOpsStatus] = useState<string>("");
  const [minPriority, setMinPriority] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const router = useRouter();

  const formatOpsStatus = (value: string) => {
    if (value === "TRUCK_SENT") return "TRUCK_DISPATCHED";
    if (value === "CLOSED") return "FALSE_POSITIVE";
    return value;
  };

  const fetchArea = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/areas`);
      if (!res.ok) return;
      const data = await res.json();
      const list = data.areas || [];
      const found = list.find((item: DashboardArea) => String(item.area_id) === params.id);
      setArea(found || null);
    } catch {
      // Ignore
    }
  };

  const fetchBins = async () => {
    try {
      const paramsQuery = new URLSearchParams({ area_id: params.id });
      if (opsStatus) paramsQuery.set("ops_status", opsStatus);
      if (minPriority > 0) paramsQuery.set("min_priority", String(minPriority));
      const res = await fetch(`${API_BASE}/api/v1/dashboard/bins?${paramsQuery.toString()}`);
      if (!res.ok) throw new Error("Failed to load bins");
      const data = await res.json();
      setBins(data.bins || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bins");
    }
  };

  const deleteArea = async () => {
    if (!window.confirm("Delete area and all its bins/captures?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/areas/${params.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete area");
      window.localStorage.setItem("areas_toast", "Area deleted");
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete area");
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
    fetchArea();
    fetchBins();
  }, []);

  useEffect(() => {
    fetchBins();
  }, [opsStatus, minPriority]);

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
              <h1 className="text-3xl font-bold text-gray-900">
                Area: {area?.area_name || params.id}
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                {area?.bins_count ?? 0} bins · {area?.captures_count ?? 0} captures
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={deleteArea}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                Delete Area
              </button>
              <Link
                href="/"
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
        {toast && <p className="text-sm text-green-700 mb-4">{toast}</p>}

        <div className="bg-white rounded-lg shadow-md p-4 mb-4">
          <div className="flex flex-wrap gap-3 items-center text-sm">
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
                    <div>
                      Status: {bin.last_status || "-"} ({((bin.last_conf || 0) * 100).toFixed(0)}%)
                    </div>
                    <div>Ops: {formatOpsStatus(bin.ops_status)}</div>
                    <div>Priority: {bin.priority_score.toFixed(0)}</div>
                    <div>Captures: {bin.capture_count}</div>
                    <div className="text-gray-500">
                      Last seen: {bin.last_seen_at ? new Date(bin.last_seen_at).toLocaleString() : "-"}
                    </div>
                  </div>
                </Link>
                <div className="flex flex-col gap-2 text-xs">
                  <Link
                    href={`/bins/${bin.id}`}
                    className="px-2 py-1 rounded border text-gray-600 hover:bg-gray-50 text-center"
                  >
                    Details
                  </Link>
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
