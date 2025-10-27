"""GitHub API client utilities."""

import os
import tempfile
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for GitHub operations."""

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            token: GitHub API token (defaults to GITHUB_TOKEN env var)
        """
        self.token = token or os.environ.get('GITHUB_ACCESS_TOKEN')
        self.session = requests.Session()

        if self.token:
            self.session.headers['Authorization'] = f'token {self.token}'
            self.session.headers['Accept'] = 'application/vnd.github.v3+json'
        
        # Rate limit tracking
        self._search_rate_limit_remaining = None
        self._search_rate_limit_reset = None
        self._last_search_time = 0
        self._min_search_interval = 2.5  # seconds between search requests (safety margin)

    def list_org_repos(self, org: str) -> List[str]:
        """List all accessible repositories in an organization.

        Args:
            org: Organization name

        Returns:
            List of repository names (org/repo format)
        """
        repos = []
        page = 1
        per_page = 100

        while True:
            url = f'https://api.github.com/orgs/{org}/repos'
            params = {
                'page': page,
                'per_page': per_page,
                'type': 'all'
            }

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()

                page_repos = response.json()
                if not page_repos:
                    break

                for repo in page_repos:
                    repos.append(f"{org}/{repo['name']}")

                page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching repos for org {org}: {e}")
                break

        return repos

    def get_repo_info(self, repo: str) -> Dict[str, Any]:
        """Get repository information.

        Args:
            repo: Repository in org/name format

        Returns:
            Repository information dictionary
        """
        url = f'https://api.github.com/repos/{repo}'

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repo info for {repo}: {e}")
            return {}

    def clone_repo(self, repo: str, target_dir: Optional[Path] = None, shallow: bool = True) -> Optional[Path]:
        """Clone a repository.

        Args:
            repo: Repository in org/name format
            target_dir: Target directory (uses temp dir if not specified)
            shallow: Whether to do a shallow clone (depth=1)

        Returns:
            Path to cloned repository or None if failed
        """
        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp(prefix='agentbom_'))
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

        repo_dir = target_dir / repo.replace('/', '_')

        # Build clone URL
        if self.token:
            clone_url = f'https://{self.token}@github.com/{repo}.git'
        else:
            clone_url = f'https://github.com/{repo}.git'

        # Clone command
        cmd = ['git', 'clone']
        if shallow:
            cmd.extend(['--depth', '1'])
        cmd.extend([clone_url, str(repo_dir)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return repo_dir
            else:
                logger.error(f"Failed to clone {repo}: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout cloning {repo}")
            return None
        except Exception as e:
            logger.error(f"Error cloning {repo}: {e}")
            return None

    def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status.
        
        Returns:
            Dictionary with rate limit info
        """
        url = 'https://api.github.com/rate_limit'
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Failed to check rate limit: {e}")
            return {}
    
    def _wait_for_rate_limit(self, reset_time: Optional[int] = None):
        """Wait until rate limit resets.
        
        Args:
            reset_time: Unix timestamp when rate limit resets
        """
        if reset_time:
            wait_seconds = reset_time - time.time()
            if wait_seconds > 0:
                wait_minutes = wait_seconds / 60
                logger.warning(
                    f"Rate limit exceeded. Waiting {wait_minutes:.1f} minutes "
                    f"until {datetime.fromtimestamp(reset_time).strftime('%H:%M:%S')}..."
                )
                time.sleep(min(wait_seconds + 5, 900))  # Wait up to 15 minutes max
    
    def _throttle_search_request(self):
        """Throttle search requests to avoid hitting rate limits."""
        # Enforce minimum interval between requests
        elapsed = time.time() - self._last_search_time
        if elapsed < self._min_search_interval:
            sleep_time = self._min_search_interval - elapsed
            logger.debug(f"Throttling: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self._last_search_time = time.time()
    
    def search_code_in_org(
        self, 
        org: str, 
        keywords: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        max_results_per_keyword: int = 100,
        smart_mode: bool = True
    ) -> List[str]:
        """Search for repositories in an org that contain specific code patterns.

        Uses GitHub's code search API to find repositories likely containing
        LLM/agent code, dramatically reducing the number of repos to scan.

        Args:
            org: Organization name
            keywords: List of keywords to search for (defaults to common LLM/agent terms)
            languages: List of languages to filter by (e.g., ['Python', 'TypeScript'])
            max_results_per_keyword: Maximum results per keyword search
            smart_mode: If True, combines keywords to reduce API calls (recommended)

        Returns:
            List of unique repository names (org/repo format)
        """
        if keywords is None:
            if smart_mode:
                # Smart mode: Top 4 keywords that catch majority of AI/LLM repos
                # Optimized for 10-request rate limit (4 queries = 2 scans possible)
                keywords = [
                    'langchain',      # Catches: LangChain, langchain-core, @langchain/*
                    'openai',         # Catches: OpenAI SDK, API usage, most common
                    'anthropic',      # Catches: Claude, Anthropic SDK
                    'agent',          # Catches: custom agents, AgentExecutor, etc.
                ]
            else:
                # Detailed mode: More granular searches (uses more API calls)
                # Each keyword is searched separately for precision
                keywords = [
                    # AI Frameworks
                    'langchain',
                    'autogen',
                    'crewai',
                    'llamaindex',
                    'haystack',
                    'semantic-kernel',
                    'dspy',
                    'guidance',
                    
                    # LLM Providers
                    'openai',
                    'anthropic',
                    'cohere',
                    'huggingface',
                    'ollama',
                    'bedrock',
                    'vertex',
                    
                    # Agent patterns
                    'agent',
                    'llm',
                    'chatbot',
                    
                    # Tools and utilities
                    'litellm',
                    'langfuse',
                    'langsmith',
                    'vectorstore',
                    'embeddings',
                ]

        repos_found = set()
        
        logger.info(
            f"Searching for agent/LLM code in org '{org}' "
            f"using {len(keywords)} search quer{'y' if len(keywords) == 1 else 'ies'} "
            f"(smart_mode={'on' if smart_mode else 'off'})"
        )
        
        total_queries = len(keywords) * (len(languages) if languages else 1)
        query_num = 0
        
        for keyword in keywords:
            # Build search query
            # Format: <keyword> org:<org> [language:<lang>]
            query_parts = [keyword, f'org:{org}']
            
            if languages:
                # GitHub uses 'in:file' for searching in file content
                query_parts.append('in:file')
            
            query = ' '.join(query_parts)
            
            # Add language filter if specified
            if languages:
                # Search for each language separately for better results
                for language in languages:
                    query_num += 1
                    lang_query = f'{query} language:{language}'
                    logger.info(f"  [{query_num}/{total_queries}] Searching: {language}...")
                    logger.debug(f"    Query: {lang_query}")
                    repos = self._search_code(lang_query, max_results_per_keyword)
                    logger.debug(f"    Found {len(repos)} unique repo(s) for this query")
                    repos_found.update(repos)
            else:
                query_num += 1
                logger.info(f"  [{query_num}/{total_queries}] Searching: '{keyword}'...")
                logger.debug(f"    Full query: {query}")
                repos = self._search_code(query, max_results_per_keyword)
                logger.debug(f"    Found {len(repos)} unique repo(s) for this query")
                repos_found.update(repos)
        
        repo_list = sorted(list(repos_found))
        logger.info(f"✓ Found {len(repo_list)} unique repository(ies) with potential agent/LLM code")
        
        return repo_list

    def _search_code(self, query: str, max_results: int = 100) -> Set[str]:
        """Execute a code search query against GitHub.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            Set of repository names (org/repo format)
        """
        repos = set()
        page = 1
        per_page = 100  # GitHub's max per page
        
        url = 'https://api.github.com/search/code'
        
        try:
            while len(repos) < max_results:
                # Throttle requests to avoid rate limits
                self._throttle_search_request()
                
                params = {
                    'q': query,
                    'page': page,
                    'per_page': min(per_page, max_results - len(repos))
                }
                
                response = self.session.get(url, params=params)
                
                # Update rate limit tracking from headers
                if 'X-RateLimit-Remaining' in response.headers:
                    self._search_rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                if 'X-RateLimit-Reset' in response.headers:
                    self._search_rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                
                # Handle rate limiting
                if response.status_code == 403 or response.status_code == 429:
                    reset_time_str = response.headers.get('X-RateLimit-Reset', 'unknown')
                    reset_time = None
                    
                    if reset_time_str != 'unknown':
                        try:
                            reset_time = int(reset_time_str)
                            reset_dt = datetime.fromtimestamp(reset_time)
                            logger.warning(
                                f"GitHub Search API rate limit exceeded. "
                                f"Resets at {reset_dt.strftime('%H:%M:%S')} ({reset_time_str})"
                            )
                        except ValueError:
                            pass
                    
                    # Check if we should wait or return what we have
                    if reset_time and (reset_time - time.time()) < 900:  # Less than 15 minutes
                        logger.info(f"Waiting for rate limit to reset...")
                        self._wait_for_rate_limit(reset_time)
                        # Retry this request
                        continue
                    else:
                        logger.warning("Rate limit wait time too long. Returning partial results.")
                        break
                
                # Check for other errors
                if response.status_code != 200:
                    logger.warning(f"Search API returned status {response.status_code}")
                    break
                
                data = response.json()
                
                # Log remaining rate limit
                if self._search_rate_limit_remaining is not None:
                    logger.debug(f"Search API rate limit remaining: {self._search_rate_limit_remaining}")
                
                items = data.get('items', [])
                total_count = data.get('total_count', 0)
                
                logger.debug(f"GitHub returned {len(items)} items (total_count: {total_count})")
                
                if not items:
                    break
                
                # Extract repository names
                for item in items:
                    repo_info = item.get('repository', {})
                    full_name = repo_info.get('full_name')
                    if full_name:
                        repos.add(full_name)
                
                # Check if we've seen all results
                total_count = data.get('total_count', 0)
                if len(items) < per_page or page * per_page >= total_count:
                    break
                
                page += 1
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error searching code for query '{query}': {e}")
        
        return repos

    def filter_repos_by_language(self, repos: List[str], languages: List[str]) -> List[str]:
        """Filter repositories by primary language.

        Args:
            repos: List of repository names (org/repo format)
            languages: List of languages to filter by (e.g., ['Python', 'TypeScript'])

        Returns:
            Filtered list of repository names
        """
        filtered = []
        
        for repo in repos:
            try:
                repo_info = self.get_repo_info(repo)
                repo_language = repo_info.get('language', '')
                
                if repo_language in languages:
                    filtered.append(repo)
                    
            except Exception as e:
                logger.debug(f"Error checking language for {repo}: {e}")
                # Include repo if we can't determine language
                filtered.append(repo)
        
        return filtered

    def cleanup_clone(self, repo_dir: Path):
        """Clean up a cloned repository.

        Args:
            repo_dir: Directory to remove
        """
        try:
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup {repo_dir}: {e}")