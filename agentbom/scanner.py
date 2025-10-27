"""Core scanning engine for AgentBOM."""

import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Any, Set

from .models import AgentBOM, Agent, Tools, ToolDetail, ToolParameter, ToolReturns
from .detectors import (
    BaseDetector,
    DetectorResult,
    LangChainPythonDetector,
    LangChainTypeScriptDetector,
    AutoGenDetector,
    CrewAIDetector,
)
from .extractors import GitExtractor
from .utils import FileWalker, GitHubClient

logger = logging.getLogger(__name__)


class Scanner:
    """Main scanner for detecting AI agents."""

    FRAMEWORK_DETECTORS = {
        'langchain-py': LangChainPythonDetector,
        'langchain-ts': LangChainTypeScriptDetector,
        'autogen': AutoGenDetector,
        'crewai': CrewAIDetector,
    }

    def __init__(
        self,
        frameworks: List[str] = None,
        strict_mode: bool = True,
        max_file_mb: float = 1.5,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        parallel: int = 8,
        llm_mode: str = 'auto',
    ):
        """Initialize scanner.

        Args:
            frameworks: List of frameworks to detect
            strict_mode: Whether to use strict detection mode
            max_file_mb: Maximum file size in MB
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            parallel: Number of parallel workers
            llm_mode: LLM enrichment mode ('auto', 'on', 'off')
        """
        self.frameworks = frameworks or ['langchain-py', 'langchain-ts']
        self.strict_mode = strict_mode
        self.max_file_mb = max_file_mb
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.parallel = parallel
        self.llm_mode = llm_mode

        # Initialize detectors
        self.detectors = []
        for framework in self.frameworks:
            if framework in self.FRAMEWORK_DETECTORS:
                detector_class = self.FRAMEWORK_DETECTORS[framework]
                self.detectors.append(detector_class(strict_mode=strict_mode))
            else:
                logger.warning(f"Unknown framework: {framework}")

        # File walker
        self.file_walker = FileWalker(
            max_file_mb=max_file_mb,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            strict=strict_mode
        )

        # GitHub client
        self.github_client = GitHubClient()

    def scan_path(self, path: Path) -> AgentBOM:
        """Scan a local path for agents.

        Args:
            path: Path to scan

        Returns:
            AgentBOM with detected agents
        """
        agents = []
        path = Path(path)

        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            return AgentBOM()

        # Initialize git extractor if it's a git repo
        git_extractor = None
        if (path / '.git').exists():
            git_extractor = GitExtractor(path)

        # Scan files
        detection_results = self._scan_files(path)

        # Convert results to Agent models
        for result in detection_results:
            agent = self._create_agent_from_result(result, path, git_extractor)
            if agent:
                agents.append(agent)

        return AgentBOM(agents=agents)

    def scan_repo(self, repo: str) -> AgentBOM:
        """Scan a GitHub repository for agents.

        Args:
            repo: Repository in org/name format

        Returns:
            AgentBOM with detected agents
        """
        # Clone repository
        with tempfile.TemporaryDirectory(prefix='agentbom_') as tmp_dir:
            tmp_path = Path(tmp_dir)

            logger.info(f"Cloning repository {repo}...")
            repo_path = self.github_client.clone_repo(repo, tmp_path, shallow=True)

            if not repo_path:
                logger.error(f"Failed to clone repository {repo}")
                return AgentBOM()

            try:
                # Scan the cloned repo
                bom = self.scan_path(repo_path)

                # Add repository information to agents
                for agent in bom.agents:
                    agent.repository = repo

                return bom

            finally:
                # Cleanup is handled by TemporaryDirectory context manager
                pass

    def scan_org(
        self,
        org: str,
        use_search: bool = True,
        search_keywords: Optional[List[str]] = None,
        search_languages: Optional[List[str]] = None,
    ) -> AgentBOM:
        """Scan repositories in a GitHub organization.

        Args:
            org: Organization name
            use_search: If True, uses GitHub search API to filter repos (recommended).
                       If False, scans all repos in the org (not recommended for large orgs).
            search_keywords: Custom keywords for search (defaults to common LLM/agent terms)
            search_languages: Languages to filter by (e.g., ['Python', 'TypeScript'])

        Returns:
            AgentBOM with detected agents from all repos
        """
        all_agents = []

        # Get list of repos
        if use_search:
            logger.info(f"Using smart search to find agent/LLM repositories in '{org}'")
            repos = self.github_client.search_code_in_org(
                org,
                keywords=search_keywords,
                languages=search_languages
            )
            
            if not repos:
                logger.warning(
                    f"No repositories found with agent/LLM code in '{org}'. "
                    "Try using --no-search to scan all repos (not recommended for large orgs)."
                )
                return AgentBOM(agents=all_agents)
        else:
            logger.warning(
                f"Scanning ALL repositories in '{org}'. "
                "This may take a long time and clone many repositories. "
                "Consider using search mode (default) instead."
            )
            repos = self.github_client.list_org_repos(org)
        
        logger.info(f"Will scan {len(repos)} repository(ies)")

        # Scan each repo
        for i, repo in enumerate(repos, 1):
            logger.info(f"[{i}/{len(repos)}] Scanning {repo}...")
            try:
                bom = self.scan_repo(repo)
                if bom.agents:
                    logger.info(f"  ✓ Found {len(bom.agents)} agent(s) in {repo}")
                    all_agents.extend(bom.agents)
                else:
                    logger.info(f"  - No agents found in {repo}")
            except Exception as e:
                logger.error(f"  ✗ Error scanning {repo}: {e}")
                continue

        logger.info(f"\nTotal: Found {len(all_agents)} agent(s) across {len(repos)} repository(ies)")
        return AgentBOM(agents=all_agents)

    def _scan_files(self, path: Path) -> List[DetectorResult]:
        """Scan files in a path for agents.

        Args:
            path: Path to scan

        Returns:
            List of detection results
        """
        results = []
        processed_files = set()

        # Collect files to scan
        files_to_scan = []
        for file_path in self.file_walker.walk(path):
            # Skip if already processed
            if str(file_path) in processed_files:
                continue

            files_to_scan.append(file_path)
            processed_files.add(str(file_path))

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = []

            for file_path in files_to_scan:
                future = executor.submit(self._process_file, file_path, path)
                futures.append(future)

            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Error processing file: {e}")

        return results

    def _process_file(self, file_path: Path, root_path: Path) -> Optional[DetectorResult]:
        """Process a single file for agent detection.

        Args:
            file_path: File to process
            root_path: Root path for relative path calculation

        Returns:
            DetectorResult if agent found, None otherwise
        """
        # Read file content
        content = self.file_walker.read_file_safely(file_path)
        if not content:
            return None

        # Try each detector
        for detector in self.detectors:
            try:
                result = detector.detect(file_path, content)
                if result and result.found:
                    # Resolve tool files if needed
                    self._resolve_tool_files(result, file_path, root_path)
                    return result
            except Exception as e:
                logger.debug(f"Detector error on {file_path}: {e}")
                continue

        return None

    def _resolve_tool_files(self, result: DetectorResult, file_path: Path, root_path: Path):
        """Resolve tool file paths.

        Args:
            result: Detection result
            file_path: File where agent was detected
            root_path: Root path for relative paths
        """
        # Add constructor file
        try:
            rel_path = file_path.relative_to(root_path)
            result.constructor_file = str(rel_path)
        except ValueError:
            result.constructor_file = str(file_path)

        # Resolve tool files (in a real implementation, we'd trace imports)
        # For now, just use the constructor file
        if not result.tool_files:
            result.tool_files = [result.constructor_file]

    def _create_agent_from_result(
        self,
        result: DetectorResult,
        root_path: Path,
        git_extractor: Optional[GitExtractor]
    ) -> Optional[Agent]:
        """Create Agent model from detection result.

        Args:
            result: Detection result
            root_path: Root path of scan
            git_extractor: Git extractor for metadata

        Returns:
            Agent model or None
        """
        try:
            # Collect all files for this agent
            agent_files = [result.constructor_file]
            agent_files.extend(result.tool_files)

            # Remove duplicates
            agent_files = list(set(agent_files))

            # Extract git metadata if available
            if git_extractor:
                owner = git_extractor.get_owner(agent_files)
                timestamps = git_extractor.get_timestamps(agent_files)
                last_changed_by = git_extractor.get_last_changed_by(agent_files)
                default_branch = git_extractor.get_default_branch()
            else:
                owner = "unknown"
                from datetime import datetime
                now = datetime.now()
                timestamps = {'created_at': now, 'updated_at': now}
                last_changed_by = None
                default_branch = None

            # Convert tools
            tool_details = []
            for tool in result.tools:
                # Convert parameters
                params = {}
                if tool.parameters:
                    for param_name, param_info in tool.parameters.items():
                        # Skip special parameters like *args, **kwargs
                        if param_name.startswith('*'):
                            continue

                        param = ToolParameter(
                            type=param_info.get('type', 'Any'),
                            required=param_info.get('required', False),
                            description=param_info.get('description')
                        )
                        params[param_name] = param

                # Convert return type
                returns = None
                if tool.returns:
                    returns = ToolReturns(
                        type=tool.returns.get('type', 'Any'),
                        description=tool.returns.get('description')
                    )

                tool_detail = ToolDetail(
                    tool_name=tool.name,
                    description=tool.description or "unknown",
                    parameters=params,
                    returns=returns
                )
                tool_details.append(tool_detail)

            tools = Tools(
                count=len(result.tools),
                details=tool_details
            )

            # Create agent
            agent = Agent(
                name=result.agent_name or root_path.name,
                repository=str(root_path),
                type=result.agent_type,
                language=result.language,
                frameworks=result.frameworks,
                architecture=result.architecture,
                description=result.metadata.get('description', ''),
                files=agent_files,
                owner=owner,
                created_at=timestamps['created_at'],
                updated_at=timestamps['updated_at'],
                x_last_changed_by=last_changed_by,
                x_repo_default_branch=default_branch,
                tools=tools,
            )

            # LLM enrichment would go here if enabled
            if self.llm_mode == 'on' or (self.llm_mode == 'auto' and self._has_llm_config()):
                # Would call LLM enrichment here
                pass

            return agent

        except Exception as e:
            logger.error(f"Error creating agent from result: {e}")
            return None

    def _has_llm_config(self) -> bool:
        """Check if LLM configuration is available."""
        import os
        return bool(os.environ.get('OPENAI_API_KEY'))