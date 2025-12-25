"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import "../../globals.css";

const API_BASE = "http://localhost:8000";

type Area = {
  id: number;
  name: string;
};

type CaptureItem = {
  id: number;
  session_id: string;
  image_url: string;
  status: string;
  conf: number;
  created_at: string;
};

type BinEvent = {
  id: number;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  note: string | null;
  created_at: string;
};

type BinDetail = {
  id: number;
  bin_key: string;
  area: Area | null;
  last_status: string | null;
  last_conf: number | null;
  capture_count: number;
  ops_status: string;
  ops_notes: string | null;
  priority_score: number;
  priority_reason: string | null;
  last_seen_at: string | null;
  updated_at: string;
  captures: CaptureItem[];
};

export default function BinDetailPage({ params }: { params: { id: string } }) {
  const [bin, setBin] = useState<BinDetail | null>(null);
  const [events, setEvents] = useState<BinEvent[]>([]);
  const [opsStatus, setOpsStatus] = useState<string>("NEW");
  const [opsNotes, setOpsNotes] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const router = useRouter();

  const normalizeOpsStatus = (value?: string | null) => {
    if (!value) return "NEW";
    if (value === "TRUCK_SENT") return "TRUCK_DISPATCHED";
    if (value === "CLOSED") return "FALSE_POSITIVE";
    return value;
  };

  const fetchBin = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/bins/${params.id}`);
      if (!res.ok) throw new Error("Failed to load bin");
      const data = await res.json();
      setBin(data);
      setOpsStatus(normalizeOpsStatus(data.ops_status));
      setOpsNotes(data.ops_notes || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bin");
    }
  };

  const fetchEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/bins/${params.id}/events`);
      if (!res.ok) return;
      const data = await res.json();
      setEvents(data.events || []);
    } catch {
      // Ignore
    }
  };

  const updateOps = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/bins/${params.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ops_status: opsStatus, ops_notes: opsNotes }),
      });
      if (!res.ok) throw new Error("Failed to update ops status");
      await fetchBin();
      await fetchEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update ops status");
    }
  };

  const markFalsePositive = async () => {
    const note = window.prompt("Optional note for false positive") || "";
    try {
      const res = await fetch(`${API_BASE}/api/v1/bins/${params.id}/false-positive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      });
      if (!res.ok) throw new Error("Failed to mark false positive");
      const payload = await res.json();
      if (payload?.hard_negative_saved) {
        setNote("Saved to hard_negatives");
      } else {
        setNote("Marked as false positive");
      }
      await fetchBin();
      await fetchEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark false positive");
    }
  };

  const deleteBin = async () => {
    if (!window.confirm("Delete this bin and all related captures?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/bins/${params.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete bin");
      window.localStorage.setItem("bins_toast", "Bin deleted");
      const target = bin?.area?.id ? `/bins?area_id=${bin.area.id}` : "/bins";
      router.push(target);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete bin");
    }
  };

  useEffect(() => {
    fetchBin();
    fetchEvents();
  }, [params.id]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Bin Detail</h1>
              <p className="text-sm text-gray-500 mt-1">Bin #{params.id}</p>
            </div>
            <Link
              href="/bins"
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
            >
              Back to Bins
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
        {note && <p className="text-sm text-green-700 mb-4">{note}</p>}
        {bin && (
          <div className="bg-white rounded-lg shadow-md p-4 space-y-6">
            <div className="text-sm text-gray-700 space-y-1">
              <div>Bin key: {bin.bin_key}</div>
              <div>Area: {bin.area?.name || "Unknown"}</div>
              <div>
                Last status: {bin.last_status || "-"} (
                {((bin.last_conf || 0) * 100).toFixed(0)}%)
              </div>
              <div>Capture count: {bin.capture_count}</div>
              <div>
                Last seen: {bin.last_seen_at ? new Date(bin.last_seen_at).toLocaleString() : "-"}
              </div>
              <div>Priority: {bin.priority_score.toFixed(0)}</div>
              <div className="text-xs text-gray-500">
                {bin.priority_reason || "Priority auto-scored"}
              </div>
            </div>

            <div className="border rounded-lg p-3">
              <div className="text-sm font-semibold mb-2">Operational Status</div>
              <div className="flex flex-wrap gap-3 items-center text-sm">
                <select
                  value={opsStatus}
                  onChange={(e) => setOpsStatus(e.target.value)}
                  className="border rounded px-2 py-1"
                >
                  <option value="NEW">NEW</option>
                  <option value="ON_PROCESS">ON_PROCESS</option>
                  <option value="TRUCK_DISPATCHED">TRUCK_DISPATCHED</option>
                  <option value="EMPTIED">EMPTIED</option>
                  <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                </select>
                <input
                  type="text"
                  value={opsNotes}
                  onChange={(e) => setOpsNotes(e.target.value)}
                  placeholder="Notes"
                  className="flex-1 min-w-[220px] border rounded px-2 py-1"
                />
                <button
                  onClick={updateOps}
                  className="px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                >
                  Save
                </button>
                <button
                  onClick={markFalsePositive}
                  className="px-3 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
                >
                  Mark False Positive
                </button>
                <button
                  onClick={deleteBin}
                  className="px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                >
                  Delete
                </button>
              </div>
            </div>

            <div>
              <div className="text-sm font-semibold mb-2">Captures</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {bin.captures.map((cap) => (
                  <div key={cap.id} className="border rounded-lg p-2">
                    <img
                      src={`${API_BASE}${cap.image_url}`}
                      alt={`Capture ${cap.id}`}
                      className="w-full h-40 object-cover rounded"
                    />
                    <div className="text-xs text-gray-600 mt-2">
                      <div>ID: {cap.id}</div>
                      <div>Status: {cap.status}</div>
                      <div>Conf: {(cap.conf * 100).toFixed(0)}%</div>
                      <div>{new Date(cap.created_at).toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
              {bin.captures.length === 0 && (
                <p className="text-sm text-gray-500">No captures found.</p>
              )}
            </div>

            <div>
              <div className="text-sm font-semibold mb-2">Events</div>
              {events.length === 0 && (
                <p className="text-sm text-gray-500">No events recorded.</p>
              )}
              <div className="space-y-2">
                {events.map((event) => (
                  <div key={event.id} className="border rounded-lg p-2 text-xs text-gray-600">
                    <div className="font-semibold">{event.event_type}</div>
                    <div>
                      {event.from_status || "-"} → {event.to_status || "-"}
                    </div>
                    {event.note && <div>Note: {event.note}</div>}
                    <div>{new Date(event.created_at).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
