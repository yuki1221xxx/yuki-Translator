"""Create a GitHub-ready split zip of the studio release folder."""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

PART_SIZE = 1_800 * 1024 * 1024  # stay under GitHub's 2 GiB asset limit


def create_zip(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=1,
    ) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(source_dir.parent))


def split_file(source: Path, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    with source.open("rb") as handle:
        index = 1
        while chunk := handle.read(PART_SIZE):
            part_path = output_dir / f"{stem}.part{index:03d}"
            part_path.write_bytes(chunk)
            parts.append(part_path)
            index += 1
    return parts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("releases/studio-v6/YukiTranslator"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("releases/studio-v6/dist"),
    )
    parser.add_argument("--name", default="YukiTranslator-v6.0.0")
    args = parser.parse_args()

    source_dir = args.source.resolve()
    output_dir = args.output_dir.resolve()
    if not source_dir.is_dir():
        print(f"Source folder not found: {source_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{args.name}.zip"
    print(f"Creating zip from {source_dir} ...")
    create_zip(source_dir, zip_path)
    size_gb = zip_path.stat().st_size / (1024**3)
    print(f"Zip size: {size_gb:.2f} GiB")

    if zip_path.stat().st_size <= PART_SIZE:
        print(f"Single asset ready: {zip_path}")
        return 0

    print("Splitting zip for GitHub release assets ...")
    parts = split_file(zip_path, output_dir, args.name)
    zip_path.unlink()
    for part in parts:
        part_gb = part.stat().st_size / (1024**3)
        print(f"  {part.name}: {part_gb:.2f} GiB")
    print(f"Created {len(parts)} parts in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
