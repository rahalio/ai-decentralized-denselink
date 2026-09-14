"""
File system utilities
"""

from pathlib import Path
from typing import Optional, Set


def remove_stale_domain_dirs(
    parent_path: Path,
    enabled_domain_names: Set[str],
    preserve: Optional[Set[str]] = None,
) -> list:
    """
    Remove subdirectories of parent_path whose names are not in enabled_domain_names.
    Used to delete generated dirs for removed/non-existing domains.
    Returns list of removed directory names.
    """
    removed = []
    preserve = preserve or set()
    if not parent_path.exists() or not parent_path.is_dir():
        return removed
    for path in parent_path.iterdir():
        if path.is_dir() and path.name not in enabled_domain_names and path.name not in preserve:
            import shutil
            shutil.rmtree(path)
            removed.append(path.name)
    return removed


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, create if it doesn't"""
    path.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to file"""
    ensure_directory(path.parent)
    path.write_text(content, encoding=encoding)


def read_file(path: Path, encoding: str = "utf-8") -> str:
    """Read file content"""
    return path.read_text(encoding=encoding)


def file_exists(path: Path) -> bool:
    """Check if file exists"""
    return path.exists() and path.is_file()


def directory_exists(path: Path) -> bool:
    """Check if directory exists"""
    return path.exists() and path.is_dir()


def clean_directory(path: Path, pattern: str = "*") -> None:
    """Clean directory contents matching pattern"""
    if not path.exists():
        return

    for file_path in path.glob(pattern):
        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)


def copy_file(source: Path, destination: Path) -> None:
    """Copy file from source to destination"""
    ensure_directory(destination.parent)
    import shutil
    shutil.copy2(source, destination)


def move_file(source: Path, destination: Path) -> None:
    """Move file from source to destination"""
    ensure_directory(destination.parent)
    import shutil
    shutil.move(source, destination)


def find_project_root(start_path: Optional[Path] = None, max_levels: int = 10) -> Path:
    """
    Find the project root directory by walking up from start_path.

    The project root is identified by the presence of:
    - packages/ directory
    - openapi/ directory
    - package.json file

    Args:
        start_path: Path to start searching from (defaults to current working directory)
        max_levels: Maximum number of directory levels to walk up (default: 10)

    Returns:
        Path to project root directory (absolute path)

    Raises:
        FileNotFoundError: If project root cannot be found within max_levels
    """
    if start_path is None:
        start_path = Path.cwd()

    # Convert to absolute path if relative
    if not start_path.is_absolute():
        start_path = start_path.resolve()

    # If start_path is a file, use its parent directory
    if start_path.is_file():
        current = start_path.parent
    else:
        current = start_path

    # Project root markers - check for packages/ or core/ directory
    # This is more flexible and works with different repository structures
    # (e.g., ddd-codegen-starter uses packages/core/openapi-core/ instead of openapi/)
    # Some projects use core/ directly instead of packages/core/
    markers = [
        "packages",
        "core",
    ]

    # Walk up directory tree
    for _ in range(max_levels):
        # Check if any marker exists at this level (OR logic, not AND)
        any_marker_exists = any((current / marker).exists() for marker in markers)

        if any_marker_exists:
            return current.resolve()

        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    # If we get here, project root wasn't found
    raise FileNotFoundError(
        f"Project root not found. Searched up from: {start_path}\n"
        f"Looking for markers: {markers}\n"
        f"Make sure you're running from within a project directory with a 'packages/' or 'core/' folder."
    )
