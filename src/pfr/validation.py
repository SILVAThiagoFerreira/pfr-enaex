from pathlib import Path

from .io import read_table
from .models import SourceFiles


def validate_columns(df, required: list[str], label: str) -> list[str]:
    missing = [col for col in required if col not in df.columns]
    return [f"{label} faltando colunas: {', '.join(missing)}"] if missing else []


def validate_sources(sources: SourceFiles, cfg: dict) -> None:
    errors: list[str] = []
    validation = cfg["validation"]

    for label, path in (("project", sources.project), ("final", sources.final)):
        if not path.exists():
            errors.append(f"Arquivo nao encontrado: {path.name}")

    if sources.project.exists():
        errors.extend(validate_columns(read_table(sources.project), validation["required_project_columns"], sources.project.name))
    if sources.final.exists():
        errors.extend(validate_columns(read_table(sources.final), validation["required_final_columns"], sources.final.name))

    if errors:
        raise ValueError("\n".join(errors))
