import os
import platform
import shutil
import subprocess
from pathlib import Path


def remove_existing_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def create_windows_directory_link(source: Path, target: Path) -> None:
    try:
        target.symlink_to(source, target_is_directory=True)
        print(f"Created symlink: {target} -> {source}")
        return
    except OSError as symlink_error:
        print(f"Symlink creation failed ({symlink_error}); trying junction.")

    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(target), str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to create backend link. "
            f"mklink output: {result.stdout} {result.stderr}"
        )
    print(f"Created junction: {target} -> {source}")


def main() -> None:
    if platform.system() != "Windows":
        print("Backend link step is only needed on Windows. Skipping.")
        return

    source = (Path(__file__).resolve().parent.parent / "dist" / "gistim").resolve()
    if not source.exists():
        raise FileNotFoundError(
            f"Backend build folder not found: {source}. Run build-backend first."
        )

    target = Path(os.environ["APPDATA"]) / "qgis-tim"
    remove_existing_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    create_windows_directory_link(source, target)


if __name__ == "__main__":
    main()
