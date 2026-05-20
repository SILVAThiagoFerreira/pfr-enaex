from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFiles:
    project: Path
    final: Path
    plan_pdf: Path | None
    histo_files: tuple[Path, ...]


@dataclass(frozen=True)
class RunResult:
    output_path: Path
    plan_id: str
    blast_date: str
    blast_time: str
    rows: int
