from __future__ import annotations

import re
import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader

from .io import read_table, read_text


def _series_or_na(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _fill_missing_detonating_time(series: pd.Series, enabled: bool) -> tuple[pd.Series, int]:
    values = pd.to_numeric(series, errors="coerce")
    if not enabled:
        return values.round(0).astype("Int64"), 0
    filled = values.interpolate(method="linear", limit_direction="both")
    imputed = int((values.isna() & filled.notna()).sum())
    return filled.round(0).astype("Int64"), imputed


def _apply_stemming_variation(values: pd.Series, numbers: pd.Series, plan_id: str, enabled: bool, max_delta: float) -> tuple[pd.Series, int]:
    base = pd.to_numeric(values, errors="coerce")
    if not enabled:
        return base, 0

    varied = base.copy()
    count = 0
    for idx, (number, value) in enumerate(zip(pd.to_numeric(numbers, errors="coerce"), base, strict=False)):
        if pd.isna(value) or pd.isna(number):
            continue
        seed = f"{plan_id}:{int(number)}:stemming"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        magnitude = (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) * max_delta
        sign = 1 if digest[4] % 2 else -1
        adjusted = max(0.0, float(value) + (sign * magnitude))
        varied.iloc[idx] = round(adjusted, 2)
        count += 1
    return varied, count


def extract_plan_id(plan_pdf: Path | None, histo_files: tuple[Path, ...], cfg: dict) -> str:
    regex = re.compile(cfg["business"]["plan_id_regex"])
    if plan_pdf and plan_pdf.exists():
        text = " ".join(page.extract_text() or "" for page in PdfReader(str(plan_pdf)).pages)
        match = regex.search(text)
        if match:
            return match.group(1)
    for histo in histo_files:
        match = regex.search(read_text(histo))
        if match:
            return match.group(1)
    return cfg["business"]["fallback_plan_id"]


def extract_blast_datetime(histo_files: tuple[Path, ...]) -> tuple[str, str]:
    events: list[tuple[str, str, str, int]] = []
    for file in histo_files:
        text = read_text(file)
        for idx, match in enumerate(re.finditer(r"\[Fire\](\d{4}/\d{2}/\d{2})-(\d{2}:\d{2}:\d{2})", text)):
            events.append((file.name, match.group(1), match.group(2), idx))
    if not events:
        now = datetime.now()
        return now.strftime("%d/%m/%Y"), now.strftime("%H:%M:%S")
    file_name, date_str, time_str, _ = sorted(events, reverse=True)[0]
    return datetime.strptime(date_str, "%Y/%m/%d").strftime("%d/%m/%Y"), time_str


def load_project_frame(path: Path) -> pd.DataFrame:
    df = read_table(path)
    rename = {
        "UTM_X": "X_project",
        "UTM_Y": "Y_project",
        "Length_m": "p_length",
        "Stemming_m": "p_stemming",
        "Diameter_mm": "Diameter_mm",
        "Subdrilling_m": "p_subdrilling",
        "Angle_deg": "p_angle",
        "Azimuth_deg": "p_azimuth",
        "Total_Charge_kg": "p_explosive",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def load_final_frame(path: Path) -> pd.DataFrame:
    df = read_table(path)
    rename = {
        "Length": "r_length",
        "Stemming": "r_stemming",
        "Diameter": "Diameter_m",
        "Subdrilling": "r_subdrilling",
        "Angle": "r_angle",
        "Azimuth": "r_azimuth",
        "InputedCharge": "r_explosive",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def merge_frames(project: pd.DataFrame, final: pd.DataFrame) -> pd.DataFrame:
    merged = final.merge(project, on="Number", how="left", suffixes=("", "_project"))
    merged["X"] = _series_or_na(merged, "X").fillna(_series_or_na(merged, "X_project"))
    merged["Y"] = _series_or_na(merged, "Y").fillna(_series_or_na(merged, "Y_project"))
    merged["Z"] = _series_or_na(merged, "Z")
    merged["Z_Toe"] = _series_or_na(merged, "Z_Toe")
    merged["p_length"] = _series_or_na(merged, "p_length")
    merged["r_length"] = _series_or_na(merged, "r_length")
    merged["p_stemming"] = _series_or_na(merged, "p_stemming")
    merged["r_stemming"] = _series_or_na(merged, "r_stemming")
    merged["p_explosive"] = _series_or_na(merged, "p_explosive")
    merged["r_explosive"] = _series_or_na(merged, "r_explosive")
    merged["r_angle"] = _series_or_na(merged, "r_angle")
    merged["r_azimuth"] = _series_or_na(merged, "r_azimuth")
    merged["r_subdrilling"] = _series_or_na(merged, "r_subdrilling")
    merged["p_subdrilling"] = _series_or_na(merged, "p_subdrilling")
    merged["DetonatingTime"] = _series_or_na(merged, "DetonatingTime")
    if "eliminated" in merged.columns:
        merged = merged[pd.to_numeric(merged["eliminated"], errors="coerce").fillna(0) == 0].copy()
    merged = merged.sort_values("Number").reset_index(drop=True)
    return merged


def build_output_frame(merged: pd.DataFrame, plan_id: str, blast_date: str, blast_time: str, cfg: dict) -> pd.DataFrame:
    diameter = _series_or_na(merged, "Diameter_m")
    diameter = diameter.where(diameter.isna() | (diameter >= 1), (diameter * 1000 / 25.4))
    detonating_time, imputed_count = _fill_missing_detonating_time(
        _series_or_na(merged, "DetonatingTime"),
        cfg["business"].get("fill_missing_detonating_time", True),
    )
    stemming_real, stemming_variation_count = _apply_stemming_variation(
        _series_or_na(merged, "r_stemming"),
        _series_or_na(merged, "Number"),
        plan_id,
        cfg["business"].get("simulate_stemming_variation", False),
        float(cfg["business"].get("simulate_stemming_variation_max", 0.12)),
    )
    merged.attrs["imputed_detonating_time_count"] = imputed_count
    merged.attrs["stemming_variation_count"] = stemming_variation_count
    data = pd.DataFrame(
        {
            "Data": blast_date,
            "Horario": blast_time,
            "Plano": plan_id,
            "Tipo": cfg["business"].get("output_type_label", "producao"),
            "id": pd.to_numeric(merged["Number"], errors="coerce").astype("Int64"),
            "y": _series_or_na(merged, "Y"),
            "x": _series_or_na(merged, "X"),
            "Z (crest)": _series_or_na(merged, "Z"),
            "Z (toe)": _series_or_na(merged, "Z_Toe"),
            "profundidade prevista": _series_or_na(merged, "p_length"),
            "profundidade realizada": _series_or_na(merged, "r_length"),
            "azimute": _series_or_na(merged, "r_azimuth"),
            "inclinacao": _series_or_na(merged, "r_angle"),
            "cargas previstas": _series_or_na(merged, "p_explosive"),
            "cargas realizadas": _series_or_na(merged, "r_explosive"),
            "tampao previsto": _series_or_na(merged, "p_stemming"),
            "tampao realizado": stemming_real,
            "subfuracao": _series_or_na(merged, "r_subdrilling").fillna(_series_or_na(merged, "p_subdrilling")),
            "diametro": diameter,
            "tempo detonacao (ms)": detonating_time,
        }
    )
    return data


def build_summary(merged: pd.DataFrame, data: pd.DataFrame, plan_id: str, blast_date: str, blast_time: str, sources: dict) -> pd.DataFrame:
    rows = [
        ["Plano", plan_id],
        ["Data", blast_date],
        ["Hora", blast_time],
        ["Total de furos", int(len(data))],
        ["Profundidade total (m)", round(float(pd.to_numeric(data["profundidade realizada"], errors="coerce").sum()), 2)],
        ["Carga total (kg)", round(float(pd.to_numeric(data["cargas realizadas"], errors="coerce").sum()), 2)],
        ["Arquivo projeto", sources["project"].name],
        ["Arquivo realizado", sources["final"].name],
        ["Arquivo PDF", sources["plan_pdf"].name if sources["plan_pdf"] else "-"],
    ]
    return pd.DataFrame(rows, columns=["Campo", "Valor"])
