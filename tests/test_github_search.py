"""Tests for GitHub search functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agentbom.utils import GitHubClient


class TestGitHubSearch:
    """Test GitHub search capabilities."""
    
    def test_search_code_in_org_with_defaults(self):
        """Test searching org with default keywords."""
        client = GitHubClient(token="test_token")
        
        with patch.object(client, '_search_code') as mock_search:
            mock_search.return_value = {'org/repo1', 'org/repo2'}
            
            repos = client.search_code_in_org('testorg')
            
            # Should have been called with multiple keywords
            assert mock_search.call_count > 0
            assert len(repos) > 0
    
    def test_search_code_in_org_with_custom_keywords(self):
        """Test searching org with custom keywords."""
        client = GitHubClient(token="test_token")
        
        custom_keywords = ['MyAgent', 'CustomFramework']
        
        with patch.object(client, '_search_code') as mock_search:
            mock_search.return_value = {'org/repo1'}
            
            repos = client.search_code_in_org(
                'testorg',
                keywords=custom_keywords
            )
            
            # Should be called for each keyword
            assert mock_search.call_count == len(custom_keywords)
    
    def test_search_code_in_org_with_languages(self):
        """Test searching org filtered by language."""
        client = GitHubClient(token="test_token")
        
        with patch.object(client, '_search_code') as mock_search:
            mock_search.return_value = {'org/repo1'}
            
            repos = client.search_code_in_org(
                'testorg',
                keywords=['test'],
                languages=['Python', 'TypeScript']
            )
            
            # Should be called for each keyword x language combination
            assert mock_search.call_count >= 2
    
    def test_search_code_returns_unique_repos(self):
        """Test that duplicate repos are deduplicated."""
        client = GitHubClient(token="test_token")
        
        with patch.object(client, '_search_code') as mock_search:
            # Simulate finding the same repo multiple times
            mock_search.return_value = {'org/repo1', 'org/repo2'}
            
            repos = client.search_code_in_org(
                'testorg',
                keywords=['keyword1', 'keyword2']
            )
            
            # Should deduplicate
            assert len(repos) == len(set(repos))
    
    def test_search_code_basic(self):
        """Test basic code search."""
        client = GitHubClient(token="test_token")
        
        # Mock the session.get method
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'X-RateLimit-Remaining': '30',
            'X-RateLimit-Reset': '1234567890'
        }
        mock_response.json.return_value = {
            'total_count': 1,
            'items': [
                {
                    'repository': {
                        'full_name': 'org/repo1'
                    }
                }
            ]
        }
        
        with patch.object(client.session, 'get', return_value=mock_response), \
             patch.object(client, '_throttle_search_request'):
            repos = client._search_code('from langchain org:testorg')
            
            assert 'org/repo1' in repos
            assert len(repos) == 1
    
    def test_search_code_handles_rate_limit(self):
        """Test that rate limiting is handled gracefully."""
        client = GitHubClient(token="test_token")
        
        # Mock rate limit response with far future reset time (> 15 min)
        import time
        far_future = int(time.time()) + 2000  # 33+ minutes in future
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(far_future)
        }
        
        with patch.object(client.session, 'get', return_value=mock_response), \
             patch.object(client, '_throttle_search_request'):
            repos = client._search_code('test query')
            
            # Should return empty set (doesn't wait for > 15 min), not crash
            assert repos == set()
    
    def test_search_code_handles_empty_results(self):
        """Test handling of empty search results."""
        client = GitHubClient(token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            'total_count': 0,
            'items': []
        }
        
        with patch.object(client.session, 'get', return_value=mock_response), \
             patch.object(client, '_throttle_search_request'):
            repos = client._search_code('nonexistent query')
            
            assert repos == set()
    
    def test_filter_repos_by_language(self):
        """Test filtering repositories by language."""
        client = GitHubClient(token="test_token")
        
        repos = ['org/python-repo', 'org/ts-repo', 'org/go-repo']
        
        # Mock get_repo_info to return different languages
        def mock_get_repo_info(repo):
            if 'python' in repo:
                return {'language': 'Python'}
            elif 'ts' in repo:
                return {'language': 'TypeScript'}
            else:
                return {'language': 'Go'}
        
        with patch.object(client, 'get_repo_info', side_effect=mock_get_repo_info):
            filtered = client.filter_repos_by_language(repos, ['Python'])
            
            assert 'org/python-repo' in filtered
            assert 'org/ts-repo' not in filtered
            assert 'org/go-repo' not in filtered


class TestScannerOrgIntegration:
    """Test scanner integration with search."""
    
    def test_scan_org_uses_search_by_default(self):
        """Test that scan_org uses search by default."""
        from agentbom.scanner import Scanner
        
        scanner = Scanner()
        
        with patch.object(scanner.github_client, 'search_code_in_org') as mock_search, \
             patch.object(scanner, 'scan_repo') as mock_scan_repo:
            
            mock_search.return_value = ['org/repo1']
            mock_scan_repo.return_value = MagicMock(agents=[])
            
            scanner.scan_org('testorg')
            
            # Should call search, not list_org_repos
            mock_search.assert_called_once()
    
    def test_scan_org_can_disable_search(self):
        """Test that search can be disabled."""
        from agentbom.scanner import Scanner
        
        scanner = Scanner()
        
        with patch.object(scanner.github_client, 'list_org_repos') as mock_list, \
             patch.object(scanner.github_client, 'search_code_in_org') as mock_search, \
             patch.object(scanner, 'scan_repo') as mock_scan_repo:
            
            mock_list.return_value = ['org/repo1', 'org/repo2']
            mock_scan_repo.return_value = MagicMock(agents=[])
            
            scanner.scan_org('testorg', use_search=False)
            
            # Should call list_org_repos, not search
            mock_list.assert_called_once()
            mock_search.assert_not_called()
    
    def test_scan_org_passes_search_params(self):
        """Test that search parameters are passed correctly."""
        from agentbom.scanner import Scanner
        
        scanner = Scanner()
        
        with patch.object(scanner.github_client, 'search_code_in_org') as mock_search, \
             patch.object(scanner, 'scan_repo') as mock_scan_repo:
            
            mock_search.return_value = []
            mock_scan_repo.return_value = MagicMock(agents=[])
            
            custom_keywords = ['MyAgent']
            custom_languages = ['Python']
            
            scanner.scan_org(
                'testorg',
                use_search=True,
                search_keywords=custom_keywords,
                search_languages=custom_languages
            )
            
            mock_search.assert_called_once_with(
                'testorg',
                keywords=custom_keywords,
                languages=custom_languages
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

