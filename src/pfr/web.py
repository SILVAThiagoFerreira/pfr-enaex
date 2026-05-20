from __future__ import annotations

import logging
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

import yaml
from flask import Flask, abort, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from .config import load_config
from .pipeline import run

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".pdf", ".txt", ".png", ".jpg", ".jpeg"}


def create_app(project_root: Path, default_config: Path) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(project_root / "src" / "pfr" / "templates"),
        static_folder=str(project_root / "src" / "pfr" / "static"),
    )
    app.config["PROJECT_ROOT"] = project_root
    app.config["DEFAULT_CONFIG"] = default_config
    app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/generate")
    def generate():
        files = [file for file in request.files.getlist("inputs") if file and file.filename]
        if not files:
            return render_template("index.html", error="Anexe ao menos um arquivo de input."), 400

        run_id = uuid.uuid4().hex[:12]
        run_root = project_root / "data" / "web_runs" / run_id
        input_root = run_root / "input"
        output_root = run_root / "output"
        input_root.mkdir(parents=True, exist_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)

        saved_files: list[str] = []
        for file in files:
            filename = _safe_upload_filename(file.filename)
            suffix = Path(filename).suffix.lower()
            if not filename or suffix not in ALLOWED_EXTENSIONS:
                shutil.rmtree(run_root, ignore_errors=True)
                return render_template("index.html", error=f"Extensao nao permitida: {suffix}"), 400
            target = input_root / filename
            file.save(target)
            saved_files.append(filename)

        config_path = _build_run_config(project_root, default_config, run_root, input_root, output_root)
        try:
            result = run(config_path)
        except Exception as exc:  # noqa: BLE001 - web layer must surface validation failures to the user
            logging.getLogger("pfr.web").exception("Falha na geracao web %s", run_id)
            return render_template(
                "index.html",
                error=str(exc),
                saved_files=saved_files,
                run_id=run_id,
            ), 400

        return render_template(
            "index.html",
            result=result,
            saved_files=saved_files,
            download_url=url_for("download", run_id=run_id, filename=result.output_path.name),
        )

    @app.get("/download/<run_id>/<path:filename>")
    def download(run_id: str, filename: str):
        safe_run_id = secure_filename(run_id)
        safe_filename = secure_filename(filename)
        output_root = (project_root / "data" / "web_runs" / safe_run_id / "output").resolve()
        target = (output_root / safe_filename).resolve()
        if output_root not in target.parents or not target.exists():
            abort(404)
        return send_file(target, as_attachment=True, download_name=target.name)

    @app.get("/visual/<path:filename>")
    def visual(filename: str):
        target = (project_root / "VISUAL" / filename).resolve()
        visual_root = (project_root / "VISUAL").resolve()
        if visual_root not in target.parents or not target.exists():
            abort(404)
        return send_file(target)

    return app


def _safe_upload_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name.strip()
    if name in {"", ".", ".."}:
        return ""
    return name


def _build_run_config(project_root: Path, default_config: Path, run_root: Path, input_root: Path, output_root: Path) -> Path:
    cfg = deepcopy(load_config(default_config))
    cfg.setdefault("paths", {})
    cfg["paths"]["project_root"] = str(project_root)
    cfg["paths"]["input_root"] = str(input_root)
    cfg["paths"]["output_root"] = str(output_root)
    cfg["paths"]["backup_root"] = str(project_root / "data" / "backup")
    cfg["paths"]["log_root"] = str(project_root / "logs")
    config_path = run_root / "config.yaml"
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg, handle, allow_unicode=True, sort_keys=False)
    return config_path
