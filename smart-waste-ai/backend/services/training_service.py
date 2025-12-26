"""
Training Service
================
Manages dataset preparation, YOLO training, and model activation.
"""

import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

from backend.config import config as backend_config
from ai.config import config as ai_config
from backend.services.inference_service import get_inference_service

try:
    import torch
except Exception:
    torch = None

_lock = threading.Lock()
_training_thread: Optional[threading.Thread] = None


def _write_status(status: Dict) -> None:
    backend_config.TRAINING_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(backend_config.TRAINING_STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def _read_status() -> Dict:
    if not backend_config.TRAINING_STATUS_FILE.exists():
        return {
            "state": "idle",
            "epoch": 0,
            "epochs": 0,
            "metrics": {},
            "logs_tail": "",
            "artifacts": {},
            "error": None,
        }
    with open(backend_config.TRAINING_STATUS_FILE, "r") as f:
        return json.load(f)


def _tail_log(lines: int = 200) -> str:
    if not backend_config.TRAINING_LOG_FILE.exists():
        return ""
    with open(backend_config.TRAINING_LOG_FILE, "r") as f:
        content = f.readlines()
    return "".join(content[-lines:])


def _append_log(message: str) -> None:
    backend_config.TRAINING_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(backend_config.TRAINING_LOG_FILE, "a") as f:
        f.write(message.rstrip() + "\n")


def _get_runs_root() -> Path:
    return backend_config.TRAINING_DIR / "runs"


def _get_run_dir(run_name: str) -> Path:
    return _get_runs_root() / run_name


def _get_artifacts(run_dir: Path) -> Dict[str, Optional[str]]:
    weights_dir = run_dir / "weights"
    artifacts = {
        "run_dir": str(run_dir),
        "best_pt": str(weights_dir / "best.pt") if (weights_dir / "best.pt").exists() else None,
        "last_pt": str(weights_dir / "last.pt") if (weights_dir / "last.pt").exists() else None,
        "results_png": str(run_dir / "results.png") if (run_dir / "results.png").exists() else None,
        "confusion_matrix_png": str(run_dir / "confusion_matrix.png") if (run_dir / "confusion_matrix.png").exists() else None,
        "metrics_json": str(run_dir / "metrics.json") if (run_dir / "metrics.json").exists() else None,
        "results_csv": str(run_dir / "results.csv") if (run_dir / "results.csv").exists() else None,
    }
    return artifacts


def _find_latest_run_dir() -> Optional[Path]:
    runs_root = _get_runs_root()
    if not runs_root.exists():
        return None
    best_candidates = list(runs_root.glob("**/weights/best.pt"))
    if not best_candidates:
        return None
    best_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return best_candidates[0].parent.parent


def _read_metrics(run_dir: Path) -> Dict:
    artifacts = _get_artifacts(run_dir)
    results_csv = artifacts.get("results_csv")
    if not results_csv:
        return {}

    try:
        with open(results_csv, "r") as f:
            lines = f.readlines()
        if len(lines) < 2:
            return {}
        header = [h.strip() for h in lines[0].split(",")]
        last = [v.strip() for v in lines[-1].split(",")]
        data = dict(zip(header, last))
        return {
            "loss": float(data.get("train/box_loss", 0.0)),
            "map50": float(data.get("metrics/mAP50(B)", 0.0)),
            "map5095": float(data.get("metrics/mAP50-95(B)", 0.0)),
        }
    except Exception:
        return {}


def _resolve_device(device: str) -> Tuple[str, Optional[str]]:
    if device == "auto":
        if torch and torch.backends.mps.is_available():
            return "mps", None
        return "cpu", None
    if device == "mps":
        if not torch or not torch.backends.mps.is_available():
            return "", "MPS is not available on this system."
        return "mps", None
    return "cpu", None


def get_status() -> Dict:
    status = _read_status()
    status["logs_tail"] = _tail_log()
    run_dir_value = status.get("run_dir")
    if run_dir_value:
        run_dir = Path(run_dir_value)
    else:
        project_name = status.get("project_name")
        run_dir = _get_run_dir(project_name) if project_name else None

    if run_dir:
        status["artifacts"] = _get_artifacts(run_dir)
        status["metrics"] = _read_metrics(run_dir)

        if not status["artifacts"].get("best_pt"):
            latest_run = _find_latest_run_dir()
            if latest_run:
                status["run_dir"] = str(latest_run)
                status["artifacts"] = _get_artifacts(latest_run)
                status["metrics"] = _read_metrics(latest_run)
                _write_status(status)
    return status


def start_training(
    model_size: str,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    project_name: str,
    dataset_yaml: Path,
) -> Dict:
    global _training_thread

    with _lock:
        status = _read_status()
        if status.get("state") == "running":
            return {"error": "Training already running"}

        resolved_device, error = _resolve_device(device)
        if error:
            return {"error": error}

        backend_config.TRAINING_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(backend_config.TRAINING_LOG_FILE, "w") as f:
            f.write("")

        status = {
            "state": "running",
            "epoch": 0,
            "epochs": epochs,
            "metrics": {},
            "logs_tail": "",
            "artifacts": {},
            "error": None,
            "project_name": project_name,
            "device": resolved_device,
            "dataset_yaml": str(dataset_yaml),
            "run_dir": None,
        }
        _write_status(status)

        def _run():
            nonlocal resolved_device
            runs_root = _get_runs_root()
            run_dir = _get_run_dir(project_name)
            yolo_cmd = shutil.which("yolo")
            cmd = None
            if yolo_cmd:
                cmd = [
                    yolo_cmd,
                    "detect",
                    "train",
                    f"data={dataset_yaml}",
                    f"model=yolo12{model_size}.pt",
                    f"epochs={epochs}",
                    f"imgsz={imgsz}",
                    f"batch={batch}",
                    f"device={resolved_device}",
                    f"project={runs_root}",
                    f"name={project_name}",
                ]

            epoch_re = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
            run_dir_re = re.compile(r"(Results saved to|Saved to)\s+(.+runs[^\s]+)")

            try:
                _append_log(f"Device: {resolved_device}")
                _append_log(f"Dataset YAML: {dataset_yaml}")
                _append_log(f"Runs dir: {runs_root}")
                _append_log(f"Expected run dir: {run_dir}")

                if cmd:
                    _append_log(f"Starting training: {' '.join(cmd)}")
                    proc = subprocess.Popen(
                        cmd,
                        cwd=str(backend_config.PROJECT_ROOT),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    with open(backend_config.TRAINING_LOG_FILE, "a") as log_file:
                        for line in proc.stdout or []:
                            log_file.write(line)
                            log_file.flush()

                            match = epoch_re.match(line)
                            if match:
                                status = _read_status()
                                status["epoch"] = int(match.group(1))
                                status["epochs"] = int(match.group(2))
                                _write_status(status)

                            run_match = run_dir_re.search(line)
                            if run_match:
                                status = _read_status()
                                status["run_dir"] = run_match.group(2).strip()
                                _write_status(status)

                    ret = proc.wait()
                else:
                    _append_log("yolo CLI not found, falling back to Ultralytics Python API")
                    try:
                        from ultralytics import YOLO
                    except Exception as e:
                        raise RuntimeError("Ultralytics not available. Install ultralytics.") from e

                    model = YOLO(f"yolo12{model_size}.pt")
                    model.train(
                        data=str(dataset_yaml),
                        epochs=epochs,
                        imgsz=imgsz,
                        batch=batch,
                        device=resolved_device,
                        project=str(runs_root),
                        name=project_name,
                    )
                    ret = 0
                status = _read_status()
                run_dir_value = status.get("run_dir")
                run_dir = Path(run_dir_value) if run_dir_value else _get_run_dir(project_name)
                status["artifacts"] = _get_artifacts(run_dir)
                status["metrics"] = _read_metrics(run_dir)
                best_pt = status["artifacts"].get("best_pt")
                if best_pt:
                    _append_log(f"Best weights: {best_pt}")
                else:
                    status["state"] = "failed"
                    status["error"] = "Training completed but best.pt was not found."
                    _write_status(status)
                    return

                if ret == 0:
                    if status.get("epoch", 0) == 0 and epochs > 0:
                        status["epoch"] = epochs
                    status["state"] = "completed"
                else:
                    status["state"] = "failed"
                    status["error"] = f"Training failed with exit code {ret}"
                _write_status(status)
            except Exception as e:
                status = _read_status()
                status["state"] = "failed"
                status["error"] = str(e)
                _write_status(status)

        _training_thread = threading.Thread(target=_run, daemon=True)
        _training_thread.start()

    return {"status": "started"}


def use_model(weights_path: str) -> Dict:
    weights_src = Path(weights_path)
    if not weights_src.exists():
        return {"error": f"Weights not found: {weights_path}"}

    backend_config.TRAINING_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = backend_config.TRAINING_WEIGHTS_DIR / "bins.pt"
    shutil.copy2(weights_src, dest_path)

    ai_config.YOLO_WEIGHTS_PATH = str(dest_path)
    ai_config.DETECT_ALL_OBJECTS = False
    ai_config.TRASH_BIN_CLASSES = ["trash_container"]

    service = get_inference_service()
    service.initialize_models()

    return service.get_service_info()
