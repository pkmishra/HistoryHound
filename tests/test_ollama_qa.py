import pytest
from unittest.mock import Mock, patch
from historyhounder.llm.ollama_qa import enhance_context_for_qa, format_context_for_prompt, answer_question_ollama


class TestEnhancedContextProcessing:
    """Test the enhanced context processing functionality."""
    
    def test_enhance_context_for_qa_empty_data(self):
        """Test enhanced context with empty data."""
        result = enhance_context_for_qa([], [])
        
        assert 'browsing_summary' in result
        assert 'domain_stats' in result
        assert 'documents' in result
        assert 'metadatas' in result
        assert result['browsing_summary']['total_visits'] == 0
    
    def test_enhance_context_for_qa_with_data(self):
        """Test enhanced context with sample data."""
        documents = [
            'GitHub is a web-based platform for version control.',
            'LinkedIn is a professional networking platform.',
            'Stack Overflow is a Q&A site for programmers.'
        ]
        
        metadatas = [
            {'url': 'https://github.com', 'title': 'GitHub', 'domain': 'github.com', 'visit_count': 25, 'visit_time': '2024-01-28T10:00:00'},
            {'url': 'https://linkedin.com', 'title': 'LinkedIn', 'domain': 'linkedin.com', 'visit_count': 15, 'visit_time': '2024-01-28T09:00:00'},
            {'url': 'https://stackoverflow.com', 'title': 'Stack Overflow', 'domain': 'stackoverflow.com', 'visit_count': 10, 'visit_time': '2024-01-28T08:00:00'}
        ]
        
        result = enhance_context_for_qa(documents, metadatas)
        
        # Check browsing summary
        assert result['browsing_summary']['total_visits'] == 50
        assert result['browsing_summary']['unique_domains'] == 3
        assert result['browsing_summary']['total_urls'] == 3
        
        # Check top domains
        top_domains = result['browsing_summary']['top_domains']
        assert len(top_domains) == 3
        assert top_domains[0][0] == 'github.com'  # Most visited
        assert top_domains[0][1]['total_visits'] == 25
        
        # Check domain stats
        domain_stats = result['domain_stats']
        assert 'github.com' in domain_stats
        assert domain_stats['github.com']['total_visits'] == 25
        assert len(domain_stats['github.com']['urls']) == 1
    
    def test_format_context_for_prompt(self):
        """Test context formatting for prompt."""
        documents = [
            'GitHub is a web-based platform for version control.',
            'LinkedIn is a professional networking platform.'
        ]
        
        metadatas = [
            {'url': 'https://github.com', 'title': 'GitHub', 'domain': 'github.com', 'visit_count': 25, 'visit_time': '2024-01-28T10:00:00'},
            {'url': 'https://linkedin.com', 'title': 'LinkedIn', 'domain': 'linkedin.com', 'visit_count': 15, 'visit_time': '2024-01-28T09:00:00'}
        ]
        
        enhanced_context = enhance_context_for_qa(documents, metadatas)
        formatted = format_context_for_prompt(enhanced_context)
        
        # Check that formatted text contains expected sections
        assert 'BROWSING SUMMARY:' in formatted
        assert 'TOP DOMAINS BY VISITS:' in formatted
        assert 'RELEVANT DOCUMENTS:' in formatted
        assert 'Total visits: 40' in formatted
        assert 'github.com: 25 visits' in formatted
        assert 'GitHub' in formatted
        assert 'LinkedIn' in formatted
    
    def test_enhance_context_handles_missing_metadata(self):
        """Test that enhanced context handles missing metadata gracefully."""
        documents = ['Test document']
        metadatas = [{'url': 'https://test.com', 'title': 'Test'}]  # Missing visit_count, domain
        
        result = enhance_context_for_qa(documents, metadatas)
        
        # Should handle missing fields gracefully
        assert result['browsing_summary']['total_visits'] == 1  # Default visit_count
        assert result['browsing_summary']['unique_domains'] == 1  # Fixed to match domain existence 