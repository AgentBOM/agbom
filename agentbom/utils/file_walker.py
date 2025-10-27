"""File system traversal and filtering utilities."""

import os
from pathlib import Path
from typing import Iterator, List, Optional, Set
import fnmatch


class FileWalker:
    """Walks directories and filters files for scanning."""

    DEFAULT_EXCLUDES = {
        'node_modules',
        '.venv',
        'venv',
        'dist',
        'build',
        'site-packages',
        '__pycache__',
        '.git',
        '.pytest_cache',
        '.mypy_cache',
        '.tox',
        '.coverage',
        '.hypothesis',
        'htmlcov',
        'wheels',
        '*.egg-info',
        '.env',
        'env',
    }

    SUPPORTED_EXTENSIONS = {
        '.py',      # Python
        '.ts',      # TypeScript
        '.tsx',     # TypeScript React
        '.js',      # JavaScript (for some TS transpiled code)
        '.jsx',     # JavaScript React
    }

    README_PATTERNS = [
        'README',
        'README.md',
        'README.txt',
        'README.rst',
        'readme.md',
        'Readme.md',
    ]

    def __init__(
        self,
        max_file_mb: float = 1.5,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        strict: bool = True
    ):
        """Initialize file walker.

        Args:
            max_file_mb: Maximum file size in MB to process
            include_patterns: Glob patterns for files to include
            exclude_patterns: Glob patterns for files to exclude
            strict: Whether to use strict mode (default excludes)
        """
        self.max_file_bytes = int(max_file_mb * 1024 * 1024)
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []

        # Build exclude set
        self.excludes = set(self.exclude_patterns)
        if strict:
            self.excludes.update(self.DEFAULT_EXCLUDES)

    def walk(self, root_path: Path) -> Iterator[Path]:
        """Walk directory and yield matching files.

        Args:
            root_path: Root directory to walk

        Yields:
            Paths to matching files
        """
        if not root_path.exists():
            return

        # If it's a file, just check it
        if root_path.is_file():
            if self._should_process_file(root_path, root_path.parent):
                yield root_path
            return

        # Walk directory
        for dirpath, dirnames, filenames in os.walk(root_path):
            dir_path = Path(dirpath)

            # Filter directories in-place to avoid walking excluded dirs
            dirnames[:] = [
                d for d in dirnames
                if not self._should_exclude_dir(d, dir_path)
            ]

            # Process files
            for filename in filenames:
                file_path = dir_path / filename

                if self._should_process_file(file_path, root_path):
                    yield file_path

    def _should_exclude_dir(self, dirname: str, parent_path: Path) -> bool:
        """Check if directory should be excluded.

        Args:
            dirname: Directory name
            parent_path: Parent directory path

        Returns:
            True if directory should be excluded
        """
        # Check against exclude patterns
        for pattern in self.excludes:
            if fnmatch.fnmatch(dirname, pattern):
                return True

        # Check full path patterns
        full_path = parent_path / dirname
        rel_path = full_path.relative_to(parent_path.parent) if parent_path.parent != full_path else Path(dirname)

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(str(rel_path), pattern):
                return True
            if fnmatch.fnmatch(dirname, pattern):
                return True

        return False

    def _should_process_file(self, file_path: Path, root_path: Path) -> bool:
        """Check if file should be processed.

        Args:
            file_path: File path to check
            root_path: Root directory for relative path calculation

        Returns:
            True if file should be processed
        """
        # Check file size
        try:
            if file_path.stat().st_size > self.max_file_bytes:
                return False
        except (OSError, IOError):
            return False

        # Check extension (unless it's a README)
        if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
            # Allow README files
            if file_path.name not in self.README_PATTERNS:
                return False

        # Calculate relative path for pattern matching
        try:
            rel_path = file_path.relative_to(root_path)
        except ValueError:
            rel_path = file_path

        # Check include patterns (if specified)
        if self.include_patterns:
            included = False
            for pattern in self.include_patterns:
                if fnmatch.fnmatch(str(rel_path), pattern):
                    included = True
                    break
            if not included:
                return False

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(str(rel_path), pattern):
                return False
            if fnmatch.fnmatch(file_path.name, pattern):
                return False

        # Check if any parent directory should be excluded
        for parent in file_path.parents:
            if parent == root_path:
                break
            if parent.name in self.excludes:
                return False

        return True

    def find_codeowners(self, root_path: Path) -> Optional[Path]:
        """Find CODEOWNERS file in repository.

        Args:
            root_path: Repository root path

        Returns:
            Path to CODEOWNERS file if found
        """
        possible_locations = [
            root_path / 'CODEOWNERS',
            root_path / '.github' / 'CODEOWNERS',
            root_path / 'docs' / 'CODEOWNERS',
        ]

        for location in possible_locations:
            if location.exists():
                return location

        return None

    def read_file_safely(self, file_path: Path) -> Optional[str]:
        """Safely read file content with encoding detection.

        Args:
            file_path: Path to file

        Returns:
            File content or None if unable to read
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, OSError, IOError):
                continue

        return None