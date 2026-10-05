from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

SKIP_BACKEND = {".venv", "__pycache__", ".pytest_cache", "site", "raw", "index", "model_cache"}
SKIP_FRONTEND = {"node_modules", ".next", "out"}
SKIP_FILES = {".env", ".env.local", "tsconfig.tsbuildinfo", "next-env.d.ts"}


def ignore(skip_dirs: set[str]):
    def _ignore(directory: str, names: list[str]) -> set[str]:
        dropped = {n for n in names if n in skip_dirs or n in SKIP_FILES}
        dropped |= {n for n in names if n.endswith((".db", ".db-shm", ".db-wal", ".pyc"))}
        return dropped

    return _ignore


def stage(target: Path) -> None:
    for name in ("Dockerfile", ".dockerignore", "README.md"):
        shutil.copy2(HERE / name, target / name)
    shutil.copytree(ROOT / "backend", target / "backend", ignore=ignore(SKIP_BACKEND))
    shutil.copytree(ROOT / "frontend", target / "frontend", ignore=ignore(SKIP_FRONTEND))
    leaked = [p for p in target.rglob("*") if p.name in SKIP_FILES]
    if leaked:
        raise RuntimeError(f"Refusing to upload private files: {leaked}")


def space_url(repo_id: str) -> str:
    return "https://" + repo_id.replace("/", "-").replace("_", "-").replace(".", "-").lower() + ".hf.space"


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish MA'NA to a Hugging Face Docker Space")
    parser.add_argument("repo_id", help="username/space-name, e.g. hala/maana-ai")
    parser.add_argument("--set-key", action="store_true", help="store LLM_API_KEY from backend/.env as a Space secret")
    args = parser.parse_args()

    api = HfApi()
    api.create_repo(args.repo_id, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
    if args.set_key:
        key = (dotenv_values(ROOT / "backend" / ".env").get("LLM_API_KEY") or "").strip()
        if not key:
            raise SystemExit("LLM_API_KEY is empty in backend/.env")
        api.add_space_secret(args.repo_id, "LLM_API_KEY", key)
        print("LLM_API_KEY stored as a Space secret")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        stage(target)
        api.upload_folder(folder_path=str(target), repo_id=args.repo_id, repo_type="space",
                          commit_message="Deploy MA'NA")
    print("Uploaded. The first build takes about 30-40 minutes.")
    print("Space:", f"https://huggingface.co/spaces/{args.repo_id}")
    print("Site:", space_url(args.repo_id))


if __name__ == "__main__":
    main()
