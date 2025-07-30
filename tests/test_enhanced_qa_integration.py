import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from historyhounder.search import llm_qa_search
from historyhounder.llm.ollama_qa import enhance_context_for_qa, format_context_for_prompt
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.embedder import get_embedder


class TestEnhancedQAIntegration:
    """Integration tests for enhanced Q&A functionality."""
    
    @pytest.fixture
    def temp_vector_store_dir(self):
        """Create a temporary directory for vector store."""
        temp_dir = tempfile.mkdtemp(prefix="test_enhanced_qa_")
        yield temp_dir
        # Clean up after test
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    
    @pytest.fixture
    def sample_browsing_data(self):
        """Create sample browsing data for testing."""
        documents = [
            "GitHub is a web-based platform for version control and collaboration.",
            "LinkedIn is a professional networking platform for business professionals.",
            "Stack Overflow is a question and answer site for programmers.",
            "YouTube is a video sharing platform owned by Google.",
            "Google is a multinational technology company specializing in internet services."
        ]
        
        metadatas = [
            {
                'url': 'https://github.com',
                'title': 'GitHub - Where the world builds software',
                'domain': 'github.com',
                'visit_count': 25,
                'visit_time': '2024-01-28T10:00:00',
                'last_visit_time': '2024-01-28T10:00:00'
            },
            {
                'url': 'https://linkedin.com',
                'title': 'LinkedIn: Log In or Sign Up',
                'domain': 'linkedin.com',
                'visit_count': 15,
                'visit_time': '2024-01-28T09:00:00',
                'last_visit_time': '2024-01-28T09:00:00'
            },
            {
                'url': 'https://stackoverflow.com',
                'title': 'Stack Overflow - Where Developers Learn, Share, & Build Careers',
                'domain': 'stackoverflow.com',
                'visit_count': 10,
                'visit_time': '2024-01-28T08:00:00',
                'last_visit_time': '2024-01-28T08:00:00'
            },
            {
                'url': 'https://youtube.com',
                'title': 'YouTube',
                'domain': 'youtube.com',
                'visit_count': 8,
                'visit_time': '2024-01-28T07:00:00',
                'last_visit_time': '2024-01-28T07:00:00'
            },
            {
                'url': 'https://google.com',
                'title': 'Google',
                'domain': 'google.com',
                'visit_count': 12,
                'visit_time': '2024-01-28T06:00:00',
                'last_visit_time': '2024-01-28T06:00:00'
            }
        ]
        
        return documents, metadatas
    
    def test_enhanced_context_processing(self, sample_browsing_data):
        """Test that enhanced context processing works correctly."""
        documents, metadatas = sample_browsing_data
        
        enhanced_context = enhance_context_for_qa(documents, metadatas)
        
        # Verify browsing summary
        summary = enhanced_context['browsing_summary']
        assert summary['total_visits'] == 70
        assert summary['unique_domains'] == 5
        assert summary['total_urls'] == 5
        
        # Verify top domains are sorted correctly
        top_domains = summary['top_domains']
        assert len(top_domains) == 5
        assert top_domains[0][0] == 'github.com'  # Most visited
        assert top_domains[0][1]['total_visits'] == 25
        assert top_domains[1][0] == 'linkedin.com'  # Second most visited
        assert top_domains[1][1]['total_visits'] == 15
        
        # Verify domain stats
        domain_stats = enhanced_context['domain_stats']
        assert 'github.com' in domain_stats
        assert domain_stats['github.com']['total_visits'] == 25
        assert len(domain_stats['github.com']['urls']) == 1
    
    def test_context_formatting(self, sample_browsing_data):
        """Test that context formatting produces readable output."""
        documents, metadatas = sample_browsing_data
        
        enhanced_context = enhance_context_for_qa(documents, metadatas)
        formatted = format_context_for_prompt(enhanced_context)
        
        # Verify key sections are present
        assert 'BROWSING SUMMARY:' in formatted
        assert 'TOP DOMAINS BY VISITS:' in formatted
        assert 'RELEVANT DOCUMENTS:' in formatted
        
        # Verify statistics are included
        assert 'Total visits: 70' in formatted
        assert 'Unique domains: 5' in formatted
        assert 'github.com: 25 visits' in formatted
        assert 'linkedin.com: 15 visits' in formatted
        
        # Verify document information is included
        assert 'GitHub - Where the world builds software' in formatted
        assert 'https://github.com' in formatted
        assert '25 visits' in formatted
    
    def test_vector_store_integration(self, temp_vector_store_dir, sample_browsing_data):
        """Test integration with vector store and enhanced Q&A."""
        documents, metadatas = sample_browsing_data
        
        # Create vector store and add documents
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        
        store.add(documents, embeddings, metadatas)
        
        # Test different question types
        test_questions = [
            "What is my most visited website?",
            "How many times did I visit GitHub?",
            "What are the top 3 domains I visit?",
            "What is GitHub?",
            "Compare my GitHub and LinkedIn usage"
        ]
        
        for question in test_questions:
            try:
                result = llm_qa_search(
                    question, 
                    top_k=5, 
                    persist_directory=temp_vector_store_dir
                )
                
                # Verify result structure
                assert 'answer' in result
                assert 'sources' in result
                assert 'enhanced_context' in result
                assert isinstance(result['answer'], str)
                assert len(result['answer']) > 0
                
                # Verify enhanced context is present
                enhanced_context = result['enhanced_context']
                assert 'browsing_summary' in enhanced_context
                assert 'domain_stats' in enhanced_context
                
                print(f"✅ Question: '{question}'")
                print(f"   Answer: {result['answer'][:100]}...")
                
            except Exception as e:
                pytest.fail(f"Failed to process question '{question}': {e}")
        
        store.close()
    
    def test_statistical_questions(self, temp_vector_store_dir, sample_browsing_data):
        """Test that statistical questions are handled correctly."""
        documents, metadatas = sample_browsing_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test statistical questions
        statistical_questions = [
            "What is my most visited website?",
            "How many times did I visit GitHub?",
            "What are my top 3 most visited sites?",
            "What's the total number of visits across all sites?"
        ]
        
        for question in statistical_questions:
            result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
            
            # Verify the answer contains statistical information
            answer = result['answer'].lower()
            
            # Should mention visit counts or rankings
            assert any(keyword in answer for keyword in [
                'visit', 'count', 'most', 'top', '25', '15', '10', 'github', 'linkedin'
            ])
            
            print(f"✅ Statistical question: '{question}'")
            print(f"   Answer contains statistical info: {len(answer)} chars")
        
        store.close()
    
    def test_domain_specific_questions(self, temp_vector_store_dir, sample_browsing_data):
        """Test that domain-specific questions are handled correctly.
        
        IMPORTANT: This test was previously passing with weak assertions that only checked
        if domain keywords appeared anywhere in the response. The original bug was that
        responses showed 'unknown (unknown): X visits' instead of actual domain names.
        Now we have strong assertions that verify actual domain names appear.
        """
        documents, metadatas = sample_browsing_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test domain-specific questions
        domain_questions = [
            "How many times did I visit GitHub?",
            "What is my LinkedIn usage?",
            "Tell me about my Stack Overflow visits",
            "What's my YouTube browsing like?"
        ]
        
        for question in domain_questions:
            result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
            
            # Verify the answer contains domain-specific information
            answer = result['answer']
            answer_lower = answer.lower()
            
            # STRONG ASSERTION: Should show actual domain names, not 'unknown'
            assert "unknown (unknown)" not in answer_lower, f"Answer should not contain 'unknown (unknown)', got: {answer}"
            assert not answer_lower.startswith("unknown"), f"Answer should not start with 'unknown', got: {answer}"
            
            # Should mention the specific domain with proper format
            expected_domains = {
                'github': ['github.com', 'github'],
                'linkedin': ['linkedin.com', 'linkedin'], 
                'stack overflow': ['stackoverflow.com', 'stack overflow'],
                'youtube': ['youtube.com', 'youtube']
            }
            
            # Find which domain this question is about
            question_lower = question.lower()
            relevant_domain = None
            for domain_key, domain_variants in expected_domains.items():
                if domain_key in question_lower:
                    relevant_domain = domain_variants
                    break
            
            if relevant_domain:
                domain_found = any(variant in answer_lower for variant in relevant_domain)
                assert domain_found, f"Expected one of {relevant_domain} in answer for question '{question}', got: {answer}"
            
            print(f"✅ Domain question: '{question}'")
            print(f"   Answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")
        
        store.close()
    
    def test_most_visited_site_question(self, temp_vector_store_dir, sample_browsing_data):
        """Test the specific question that was failing: 'Site with the most number of visits today'."""
        documents, metadatas = sample_browsing_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test the exact question that was showing 'unknown (unknown)'
        question = "Site with the most number of visits today"
        result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
        
        answer = result['answer']
        answer_lower = answer.lower()
        
        print(f"\n🧪 Testing specific failing question: '{question}'")
        print(f"📝 Answer: {answer}")
        
        # CRITICAL: This should NOT show 'unknown (unknown)'
        assert "unknown (unknown)" not in answer_lower, f"CRITICAL: Answer contains 'unknown (unknown)', this was the original bug! Answer: {answer}"
        assert not answer_lower.startswith("unknown"), f"Answer should not start with 'unknown', got: {answer}"
        
        # Should show an actual domain name
        common_domains = ['github.com', 'linkedin.com', 'stackoverflow.com', 'youtube.com', 'example.com']
        domain_found = any(domain in answer_lower for domain in common_domains)
        
        # If no common domains found, at least check for domain-like patterns
        if not domain_found:
            import re
            domain_pattern = r'\b\w+\.\w+\b'  # Basic pattern like "site.com"
            domain_matches = re.findall(domain_pattern, answer_lower)
            assert domain_matches, f"Expected to find domain names (like 'site.com') in answer, got: {answer}"
        
        # Should mention visit counts or statistics
        stats_keywords = ['visit', 'most', 'frequent', 'count']
        stats_found = any(keyword in answer_lower for keyword in stats_keywords)
        assert stats_found, f"Expected statistical information in answer, got: {answer}"
        
        store.close()
    
    def test_semantic_questions(self, temp_vector_store_dir, sample_browsing_data):
        """Test that semantic questions are handled correctly."""
        documents, metadatas = sample_browsing_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test semantic questions
        semantic_questions = [
            "What is GitHub?",
            "Tell me about LinkedIn",
            "What is Stack Overflow?",
            "Explain what YouTube is"
        ]
        
        for question in semantic_questions:
            result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
            
            # Verify the answer contains explanatory content
            answer = result['answer'].lower()
            
            # Should contain explanatory keywords or be substantive
            has_keywords = any(keyword in answer for keyword in [
                'platform', 'service', 'website', 'site', 'company', 'tool'
            ])
            is_substantive = len(answer) > 50  # At least substantial content
            
            assert has_keywords or is_substantive, f"Answer should contain explanatory keywords or be substantive (got: {answer[:100]}...)"
            
            print(f"✅ Semantic question: '{question}'")
            print(f"   Answer contains explanation: {len(answer)} chars")
        
        store.close()
    
    def test_enhanced_context_structure(self, sample_browsing_data):
        """Test that enhanced context has the correct structure."""
        documents, metadatas = sample_browsing_data
        
        enhanced_context = enhance_context_for_qa(documents, metadatas)
        
        # Verify all required keys are present
        required_keys = ['browsing_summary', 'domain_stats', 'documents', 'metadatas']
        for key in required_keys:
            assert key in enhanced_context
        
        # Verify browsing summary structure
        summary = enhanced_context['browsing_summary']
        summary_keys = ['total_visits', 'unique_domains', 'total_urls', 'top_domains', 'most_visited_domain']
        for key in summary_keys:
            assert key in summary
        
        # Verify domain stats structure
        domain_stats = enhanced_context['domain_stats']
        assert isinstance(domain_stats, dict)
        
        # Verify at least one domain has the correct structure
        if domain_stats:
            first_domain = list(domain_stats.keys())[0]
            domain_data = domain_stats[first_domain]
            domain_keys = ['total_visits', 'urls', 'titles', 'visit_times']
            for key in domain_keys:
                assert key in domain_data
    
    def test_empty_data_handling(self):
        """Test that empty data is handled gracefully."""
        enhanced_context = enhance_context_for_qa([], [])
        
        # Verify structure is maintained
        assert 'browsing_summary' in enhanced_context
        assert 'domain_stats' in enhanced_context
        assert 'documents' in enhanced_context
        assert 'metadatas' in enhanced_context
        
        # Verify default values
        summary = enhanced_context['browsing_summary']
        assert summary['total_visits'] == 0
        assert summary['unique_domains'] == 0
        assert summary['total_urls'] == 0
        assert summary['top_domains'] == []
        assert summary['most_visited_domain'] is None
        
        # Test formatting with empty data
        formatted = format_context_for_prompt(enhanced_context)
        assert 'BROWSING SUMMARY:' in formatted
        assert 'Total visits: 0' in formatted 