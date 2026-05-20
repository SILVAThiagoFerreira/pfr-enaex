from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pfr.pipeline import run  # noqa: E402
from pfr.web import create_app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="PFR - Plano de Fogo Realizado")
    parser.add_argument("--config", default="config.yaml", help="Arquivo de configuracao")
    parser.add_argument("--web", action="store_true", help="Inicia a interface web")
    parser.add_argument("--host", default="127.0.0.1", help="Host da interface web")
    parser.add_argument("--port", type=int, default=5000, help="Porta da interface web")
    args = parser.parse_args()
    if args.web:
        app = create_app(ROOT, ROOT / args.config)
        app.run(host=args.host, port=args.port, debug=False)
        return 0
    run(ROOT / args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
