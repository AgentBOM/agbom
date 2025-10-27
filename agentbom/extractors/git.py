"""Git metadata extraction."""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess
import logging

logger = logging.getLogger(__name__)


class GitExtractor:
    """Extracts git metadata for agents."""

    def __init__(self, repo_path: Path):
        """Initialize git extractor.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path
        self._codeowners_cache = None

    def get_owner(self, files: List[str]) -> str:
        """Get owner for a set of files.

        Args:
            files: List of file paths relative to repo root

        Returns:
            Owner string (email or CODEOWNERS entry or "unknown")
        """
        # Try CODEOWNERS first
        codeowners_owner = self._get_codeowners_owner(files)
        if codeowners_owner:
            return codeowners_owner

        # Fall back to modal last author
        return self._get_modal_author(files)

    def get_timestamps(self, files: List[str]) -> Dict[str, datetime]:
        """Get creation and update timestamps for files.

        Args:
            files: List of file paths relative to repo root

        Returns:
            Dictionary with 'created_at' and 'updated_at' timestamps
        """
        created_at = None
        updated_at = None

        for file_path in files:
            # Get earliest commit (creation)
            creation = self._get_file_creation_time(file_path)
            if creation:
                if created_at is None or creation < created_at:
                    created_at = creation

            # Get latest commit (update)
            update = self._get_file_update_time(file_path)
            if update:
                if updated_at is None or update > updated_at:
                    updated_at = update

        # Fallback to current time if git info not available
        now = datetime.now()
        return {
            'created_at': created_at or now,
            'updated_at': updated_at or now,
        }

    def get_last_changed_by(self, files: List[str]) -> Optional[str]:
        """Get author of the most recent change to any file.

        Args:
            files: List of file paths relative to repo root

        Returns:
            Author string or None
        """
        latest_author = None
        latest_time = None

        for file_path in files:
            author, timestamp = self._get_last_author(file_path)
            if timestamp:
                if latest_time is None or timestamp > latest_time:
                    latest_time = timestamp
                    latest_author = author

        return latest_author

    def get_default_branch(self) -> Optional[str]:
        """Get default branch name.

        Returns:
            Default branch name or None
        """
        try:
            # Try to get the default branch
            result = subprocess.run(
                ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Extract branch name from refs/remotes/origin/main
                branch = result.stdout.strip()
                if '/' in branch:
                    return branch.split('/')[-1]

            # Fallback: try common default branch names
            for branch in ['main', 'master']:
                result = subprocess.run(
                    ['git', 'show-ref', '--verify', f'refs/heads/{branch}'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return branch

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            logger.debug(f"Error getting default branch: {e}")

        return None

    def _get_codeowners_owner(self, files: List[str]) -> Optional[str]:
        """Get owner from CODEOWNERS file.

        Args:
            files: List of file paths

        Returns:
            Owner string or None
        """
        if self._codeowners_cache is None:
            self._load_codeowners()

        if not self._codeowners_cache:
            return None

        # Find longest matching pattern
        owners = set()
        for file_path in files:
            owner = self._match_codeowners_pattern(file_path)
            if owner:
                owners.add(owner)

        # If all files have the same owner, return it
        if len(owners) == 1:
            return owners.pop()

        return None

    def _load_codeowners(self):
        """Load and parse CODEOWNERS file."""
        self._codeowners_cache = []

        possible_locations = [
            self.repo_path / 'CODEOWNERS',
            self.repo_path / '.github' / 'CODEOWNERS',
            self.repo_path / 'docs' / 'CODEOWNERS',
        ]

        codeowners_path = None
        for location in possible_locations:
            if location.exists():
                codeowners_path = location
                break

        if not codeowners_path:
            return

        try:
            content = codeowners_path.read_text()
            for line in content.splitlines():
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse pattern and owners
                parts = line.split()
                if len(parts) >= 2:
                    pattern = parts[0]
                    owners = ' '.join(parts[1:])
                    self._codeowners_cache.append((pattern, owners))

        except Exception as e:
            logger.debug(f"Error reading CODEOWNERS: {e}")

    def _match_codeowners_pattern(self, file_path: str) -> Optional[str]:
        """Match file path against CODEOWNERS patterns.

        Args:
            file_path: File path relative to repo root

        Returns:
            Owner string or None
        """
        if not self._codeowners_cache:
            return None

        # Normalize path
        if not file_path.startswith('/'):
            file_path = '/' + file_path

        # Find longest matching pattern
        best_match = None
        best_length = 0

        for pattern, owners in self._codeowners_cache:
            if self._pattern_matches(pattern, file_path):
                pattern_length = len(pattern)
                if pattern_length > best_length:
                    best_length = pattern_length
                    best_match = owners

        return best_match

    def _pattern_matches(self, pattern: str, path: str) -> bool:
        """Check if CODEOWNERS pattern matches path.

        Args:
            pattern: CODEOWNERS pattern
            path: File path

        Returns:
            True if pattern matches
        """
        # Convert CODEOWNERS pattern to regex
        # This is a simplified implementation
        regex_pattern = pattern.replace('*', '[^/]*').replace('**', '.*')

        # Add anchors
        if not regex_pattern.startswith('/'):
            regex_pattern = '.*' + regex_pattern
        else:
            regex_pattern = '^' + regex_pattern

        if regex_pattern.endswith('/'):
            regex_pattern = regex_pattern + '.*'

        regex_pattern = regex_pattern + '$'

        try:
            return re.match(regex_pattern, path) is not None
        except re.error:
            return False

    def _get_modal_author(self, files: List[str]) -> str:
        """Get most common author across files.

        Args:
            files: List of file paths

        Returns:
            Most common author or "unknown"
        """
        authors = []

        for file_path in files:
            author, _ = self._get_last_author(file_path)
            if author:
                authors.append(author)

        if authors:
            # Find most common author
            author_counts = Counter(authors)
            return author_counts.most_common(1)[0][0]

        return "unknown"

    def _get_last_author(self, file_path: str) -> tuple[Optional[str], Optional[datetime]]:
        """Get last author and timestamp for a file.

        Args:
            file_path: File path relative to repo root

        Returns:
            Tuple of (author string, timestamp)
        """
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%an <%ae>|%aI', '--', file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) == 2:
                    author = parts[0]
                    timestamp = datetime.fromisoformat(parts[1].replace('Z', '+00:00'))
                    return author, timestamp

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            logger.debug(f"Error getting last author for {file_path}: {e}")

        return None, None

    def _get_file_creation_time(self, file_path: str) -> Optional[datetime]:
        """Get creation time (earliest commit) for a file.

        Args:
            file_path: File path relative to repo root

        Returns:
            Creation timestamp or None
        """
        try:
            result = subprocess.run(
                ['git', 'log', '--reverse', '-1', '--pretty=%aI', '--', file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                return datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            logger.debug(f"Error getting creation time for {file_path}: {e}")

        return None

    def _get_file_update_time(self, file_path: str) -> Optional[datetime]:
        """Get update time (latest commit) for a file.

        Args:
            file_path: File path relative to repo root

        Returns:
            Update timestamp or None
        """
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%aI', '--', file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                return datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            logger.debug(f"Error getting update time for {file_path}: {e}")

        return None