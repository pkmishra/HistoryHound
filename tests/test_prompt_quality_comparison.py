import pytest
import tempfile
from historyhounder.search import llm_qa_search
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.embedder import get_embedder


class TestPromptQualityComparison:
    """Test to compare the quality of old vs new prompt approaches."""
    
    @pytest.fixture
    def temp_vector_store_dir(self):
        """Create a temporary directory for vector store."""
        temp_dir = tempfile.mkdtemp(prefix="test_prompt_quality_")
        yield temp_dir
        # Clean up after test
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for quality comparison."""
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
                'visit_time': '2024-01-28T10:00:00'
            },
            {
                'url': 'https://linkedin.com',
                'title': 'LinkedIn: Log In or Sign Up',
                'domain': 'linkedin.com',
                'visit_count': 15,
                'visit_time': '2024-01-28T09:00:00'
            },
            {
                'url': 'https://stackoverflow.com',
                'title': 'Stack Overflow - Where Developers Learn, Share, & Build Careers',
                'domain': 'stackoverflow.com',
                'visit_count': 10,
                'visit_time': '2024-01-28T08:00:00'
            },
            {
                'url': 'https://youtube.com',
                'title': 'YouTube',
                'domain': 'youtube.com',
                'visit_count': 8,
                'visit_time': '2024-01-28T07:00:00'
            },
            {
                'url': 'https://google.com',
                'title': 'Google',
                'domain': 'google.com',
                'visit_count': 12,
                'visit_time': '2024-01-28T06:00:00'
            }
        ]
        
        return documents, metadatas
    
    def test_enhanced_prompt_quality_improvements(self, temp_vector_store_dir, sample_data):
        """Test that the enhanced prompt provides better quality answers."""
        documents, metadatas = sample_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test questions that should show quality improvements
        test_cases = [
            {
                'question': 'What is my most visited website?',
                'expected_improvements': ['visit count', '25 visits', 'github.com', 'most visited']
            },
            {
                'question': 'How many times did I visit GitHub?',
                'expected_improvements': ['25 visits', 'github.com', 'visit count']
            },
            {
                'question': 'What are my top 3 most visited sites?',
                'expected_improvements': ['github.com', 'linkedin.com', 'stackoverflow.com', '25', '15', '10']
            },
            {
                'question': 'Compare my GitHub and LinkedIn usage',
                'expected_improvements': ['github', 'linkedin', '25', '15', 'compare', 'usage']
            }
        ]
        
        for test_case in test_cases:
            question = test_case['question']
            expected_improvements = test_case['expected_improvements']
            
            try:
                result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
                answer = result['answer'].lower()
                
                # Check that the answer contains expected improvements
                improvement_count = 0
                for improvement in expected_improvements:
                    if improvement in answer:
                        improvement_count += 1
                
                # At least 50% of expected improvements should be present
                improvement_ratio = improvement_count / len(expected_improvements)
                assert improvement_ratio >= 0.5, f"Only {improvement_ratio:.1%} of expected improvements found in answer"
                
                # Check that answer is substantial (not just a few words)
                assert len(answer) > 50, f"Answer too short: {len(answer)} characters"
                
                # Check that answer contains statistical information
                has_stats = any(keyword in answer for keyword in ['visit', 'count', '25', '15', '10', '8', '12'])
                assert has_stats, "Answer should contain statistical information"
                
                print(f"✅ Quality test passed for: '{question}'")
                print(f"   Answer length: {len(answer)} chars")
                print(f"   Improvements found: {improvement_count}/{len(expected_improvements)}")
                print(f"   Answer preview: {answer[:100]}...")
                
            except Exception as e:
                pytest.fail(f"Failed to process question '{question}': {e}")
        
        store.close()
    
    def test_enhanced_context_presence(self, temp_vector_store_dir, sample_data):
        """Test that enhanced context is properly included in responses."""
        documents, metadatas = sample_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test that enhanced context is present in results
        result = llm_qa_search("What is my most visited website?", top_k=5, persist_directory=temp_vector_store_dir)
        
        # Verify enhanced context is included
        assert 'enhanced_context' in result
        enhanced_context = result['enhanced_context']
        
        # Verify browsing summary is present
        assert 'browsing_summary' in enhanced_context
        summary = enhanced_context['browsing_summary']
        
        # Verify key statistics are correct
        assert summary['total_visits'] == 70
        assert summary['unique_domains'] == 5
        assert summary['total_urls'] == 5
        
        # Verify top domains are present
        assert 'top_domains' in summary
        assert len(summary['top_domains']) > 0
        
        # Verify domain stats are present
        assert 'domain_stats' in enhanced_context
        domain_stats = enhanced_context['domain_stats']
        assert 'github.com' in domain_stats
        assert domain_stats['github.com']['total_visits'] == 25
        
        print("✅ Enhanced context properly included in response")
        print(f"   Total visits: {summary['total_visits']}")
        print(f"   Unique domains: {summary['unique_domains']}")
        print(f"   Top domain: {summary['top_domains'][0][0]} with {summary['top_domains'][0][1]['total_visits']} visits")
        
        store.close()
    
    def test_answer_structure_improvements(self, temp_vector_store_dir, sample_data):
        """Test that answers have better structure and formatting."""
        documents, metadatas = sample_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test questions that should have structured answers
        structured_questions = [
            "What is my most visited website?",
            "How many times did I visit GitHub?",
            "What are the top 3 domains I visit?"
        ]
        
        for question in structured_questions:
            result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
            answer = result['answer']
            
            # Check for structured elements
            has_numbers = any(char.isdigit() for char in answer)
            has_urls = 'http' in answer or 'github.com' in answer or 'linkedin.com' in answer
            has_evidence = any(keyword in answer.lower() for keyword in ['visit', 'count', 'times', 'visits'])
            
            # Answer should have at least 2 of these structured elements
            structured_elements = sum([has_numbers, has_urls, has_evidence])
            assert structured_elements >= 2, f"Answer lacks structured elements: {answer[:100]}"
            
            print(f"✅ Structured answer for: '{question}'")
            print(f"   Has numbers: {has_numbers}")
            print(f"   Has URLs: {has_urls}")
            print(f"   Has evidence: {has_evidence}")
            print(f"   Answer preview: {answer[:80]}...")
        
        store.close()
    
    def test_comprehensive_answer_coverage(self, temp_vector_store_dir, sample_data):
        """Test that answers cover multiple aspects of the question."""
        documents, metadatas = sample_data
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test comprehensive questions
        comprehensive_questions = [
            "What is my most visited website?",
            "How many times did I visit GitHub?",
            "What are my top 3 most visited sites?"
        ]
        
        for question in comprehensive_questions:
            result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
            answer = result['answer'].lower()
            
            # Check for comprehensive coverage
            has_direct_answer = len(answer) > 30  # Substantial answer
            has_supporting_data = any(keyword in answer for keyword in ['visit', 'count', '25', '15', '10'])
            has_context = any(keyword in answer for keyword in ['github', 'linkedin', 'stack', 'youtube', 'google'])
            
            # Should have comprehensive coverage
            coverage_score = sum([has_direct_answer, has_supporting_data, has_context])
            assert coverage_score >= 2, f"Insufficient coverage for: {question}"
            
            print(f"✅ Comprehensive coverage for: '{question}'")
            print(f"   Direct answer: {has_direct_answer}")
            print(f"   Supporting data: {has_supporting_data}")
            print(f"   Context: {has_context}")
            print(f"   Coverage score: {coverage_score}/3")
        
        store.close() 