"use client";

import { useEffect, useRef, useState } from "react";

type BBox = { x: number; y: number; w: number; h: number };

interface AnnotationModalProps {
  imageUrl: string;
  filename: string;
  onClose: () => void;
  onSave: (bbox: BBox) => void;
}

export default function AnnotationModal({
  imageUrl,
  filename,
  onClose,
  onSave,
}: AnnotationModalProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);
  const [bbox, setBbox] = useState<BBox | null>(null);

  useEffect(() => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    const onLoad = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      draw();
    };

    if (img.complete) {
      onLoad();
    } else {
      img.onload = onLoad;
    }
  }, [imageUrl]);

  const getCanvasCoords = (e: React.MouseEvent<HTMLCanvasElement, MouseEvent>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const draw = (tempBox?: BBox) => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    const box = tempBox || bbox;
    if (box) {
      ctx.strokeStyle = "#16a34a";
      ctx.lineWidth = 3;
      ctx.strokeRect(box.x, box.y, box.w, box.h);
    }
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement, MouseEvent>) => {
    const point = getCanvasCoords(e);
    setStart(point);
    setDrawing(true);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement, MouseEvent>) => {
    if (!drawing || !start) return;
    const current = getCanvasCoords(e);
    const x = Math.min(start.x, current.x);
    const y = Math.min(start.y, current.y);
    const w = Math.abs(current.x - start.x);
    const h = Math.abs(current.y - start.y);
    draw({ x, y, w, h });
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement, MouseEvent>) => {
    if (!drawing || !start) return;
    const current = getCanvasCoords(e);
    const x = Math.min(start.x, current.x);
    const y = Math.min(start.y, current.y);
    const w = Math.abs(current.x - start.x);
    const h = Math.abs(current.y - start.y);
    setBbox({ x, y, w, h });
    setDrawing(false);
    setStart(null);
    draw({ x, y, w, h });
  };

  const handleClear = () => {
    setBbox(null);
    draw();
  };

  const handleSave = () => {
    if (!bbox || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const normalized = {
      x: Number(((bbox.x + bbox.w / 2) / canvas.width).toFixed(6)),
      y: Number(((bbox.y + bbox.h / 2) / canvas.height).toFixed(6)),
      w: Number((bbox.w / canvas.width).toFixed(6)),
      h: Number((bbox.h / canvas.height).toFixed(6)),
    };
    onSave(normalized);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[90vw] max-w-5xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Annotate Image</h2>
            <p className="text-sm text-gray-500">{filename}</p>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
          >
            Close
          </button>
        </div>

        <div className="border rounded-lg overflow-hidden bg-gray-50">
          <img ref={imgRef} src={imageUrl} alt={filename} className="hidden" />
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            className="w-full h-auto cursor-crosshair"
          />
        </div>

        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Label: <span className="font-semibold">trash_container</span>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleClear}
              className="px-4 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
            >
              Clear Box
            </button>
            <button
              onClick={handleSave}
              disabled={!bbox}
              className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-300"
            >
              Save Annotation
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
