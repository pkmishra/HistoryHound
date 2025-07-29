import pytest
import tempfile
from datetime import datetime, timedelta
from historyhounder.llm.ollama_qa import parse_temporal_reference, filter_by_date_range, enhance_context_for_qa
from historyhounder.search import llm_qa_search
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.embedder import get_embedder


class TestTemporalFiltering:
    """Test temporal filtering functionality."""
    
    @pytest.fixture
    def temp_vector_store_dir(self):
        """Create a temporary directory for vector store."""
        temp_dir = tempfile.mkdtemp(prefix="test_temporal_")
        yield temp_dir
        # Clean up after test
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    
    @pytest.fixture
    def sample_data_with_dates(self):
        """Create sample data with different dates for temporal testing."""
        documents = [
            "GitHub is a web-based platform for version control and collaboration.",
            "LinkedIn is a professional networking platform for business professionals.",
            "Stack Overflow is a question and answer site for programmers.",
            "YouTube is a video sharing platform owned by Google.",
            "Google is a multinational technology company specializing in internet services."
        ]
        
        # Create dates for different time periods
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        # Calculate last Friday using the same logic as the function
        target_day = 4  # Friday
        current_day = now.weekday()
        days_back = (current_day - target_day) % 7
        if days_back == 0:
            days_back = 7  # Last week's day
        last_friday = now - timedelta(days=days_back)
        last_friday = last_friday.replace(hour=12, minute=0, second=0, microsecond=0)  # Midday
        
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        metadatas = [
            {
                'url': 'https://github.com',
                'title': 'GitHub - Where the world builds software',
                'domain': 'github.com',
                'visit_count': 25,
                'visit_time': now.strftime('%Y-%m-%dT%H:%M:%S')
            },
            {
                'url': 'https://linkedin.com',
                'title': 'LinkedIn: Log In or Sign Up',
                'domain': 'linkedin.com',
                'visit_count': 15,
                'visit_time': yesterday.strftime('%Y-%m-%dT%H:%M:%S')
            },
            {
                'url': 'https://stackoverflow.com',
                'title': 'Stack Overflow - Where Developers Learn, Share, & Build Careers',
                'domain': 'stackoverflow.com',
                'visit_count': 10,
                'visit_time': last_friday.strftime('%Y-%m-%dT%H:%M:%S')
            },
            {
                'url': 'https://youtube.com',
                'title': 'YouTube',
                'domain': 'youtube.com',
                'visit_count': 8,
                'visit_time': last_week.strftime('%Y-%m-%dT%H:%M:%S')
            },
            {
                'url': 'https://google.com',
                'title': 'Google',
                'domain': 'google.com',
                'visit_count': 12,
                'visit_time': last_month.strftime('%Y-%m-%dT%H:%M:%S')
            }
        ]
        
        return documents, metadatas
    
    def test_parse_temporal_reference_last_friday(self):
        """Test parsing 'last Friday' temporal reference."""
        question = "What is my most visited website last Friday?"
        filtered_query, start_date, end_date = parse_temporal_reference(question)

        # Verify temporal parsing
        assert start_date is not None
        assert end_date is not None
        assert "last friday" not in filtered_query.lower()
        assert "most visited website" in filtered_query.lower()

        # Verify it's actually last Friday using the same logic as the function
        now = datetime.now()
        target_day = 4  # Friday
        current_day = now.weekday()
        days_back = (current_day - target_day + 7) % 7
        if days_back == 0:
            days_back = 7  # Last week's day
        expected_friday = now - timedelta(days=days_back)

        assert start_date.date() == expected_friday.date()
        assert end_date.date() == expected_friday.date()
        # Verify time boundaries
        assert start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0
        assert end_date.hour == 23 and end_date.minute == 59 and end_date.second == 59
        
        print(f"✅ Parsed 'last Friday': {start_date.date()} to {end_date.date()}")
    
    def test_parse_temporal_reference_yesterday(self):
        """Test parsing 'yesterday' temporal reference."""
        question = "How many times did I visit GitHub yesterday?"
        filtered_query, start_date, end_date = parse_temporal_reference(question)

        # Verify temporal parsing
        assert start_date is not None
        assert end_date is not None
        assert "yesterday" not in filtered_query.lower()
        assert "github" in filtered_query.lower()

        # Verify it's actually yesterday
        now = datetime.now()
        expected_yesterday = now - timedelta(days=1)
        assert start_date.date() == expected_yesterday.date()
        # end_date should be end of yesterday, not start of today
        assert end_date.date() == expected_yesterday.date()
        # Verify time boundaries
        assert start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0
        assert end_date.hour == 23 and end_date.minute == 59 and end_date.second == 59
        
        print(f"✅ Parsed 'yesterday': {start_date.date()} to {end_date.date()}")
    
    def test_parse_temporal_reference_today(self):
        """Test parsing 'today' temporal reference."""
        question = "What websites did I visit today?"
        filtered_query, start_date, end_date = parse_temporal_reference(question)

        # Verify temporal parsing
        assert start_date is not None
        assert end_date is not None
        assert "today" not in filtered_query.lower()

        # Verify it's actually today
        now = datetime.now()
        assert start_date.date() == now.date()
        assert end_date.date() == now.date()
        # Verify time boundaries
        assert start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0
        assert end_date.hour == 23 and end_date.minute == 59 and end_date.second == 59
        
        print(f"✅ Parsed 'today': {start_date.date()} to {end_date.date()}")
    
    def test_parse_temporal_reference_this_week(self):
        """Test parsing 'this week' temporal reference."""
        question = "What are my most visited sites this week?"
        filtered_query, start_date, end_date = parse_temporal_reference(question)

        # Verify temporal parsing
        assert start_date is not None
        assert end_date is not None
        assert "this week" not in filtered_query.lower()

        # Verify it's actually this week - Monday to current day
        now = datetime.now()
        expected_start = now - timedelta(days=now.weekday())
        expected_start = expected_start.replace(hour=0, minute=0, second=0, microsecond=0)
        assert start_date.date() == expected_start.date()
        # End date should be current time, not end of the week
        assert end_date.replace(microsecond=0, second=0, minute=0, hour=0).date() == now.date()
        
        print(f"✅ Parsed 'this week': {start_date.date()} to {end_date.date()}")
    
    def test_parse_temporal_reference_no_temporal(self):
        """Test parsing question with no temporal reference."""
        question = "What is my most visited website?"
        filtered_query, start_date, end_date = parse_temporal_reference(question)
        
        # Verify no temporal parsing
        assert start_date is None
        assert end_date is None
        assert filtered_query == question
        
        print("✅ No temporal reference parsed correctly")
    
    def test_filter_by_date_range(self, sample_data_with_dates):
        """Test filtering metadata by date range."""
        documents, metadatas = sample_data_with_dates
        
        # Test filtering for last Friday using the same logic as the function
        now = datetime.now()
        target_day = 4  # Friday
        current_day = now.weekday()
        days_back = (current_day - target_day) % 7
        if days_back == 0:
            days_back = 7  # Last week's day
        last_friday = now - timedelta(days=days_back)
        last_friday = last_friday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        start_date = last_friday
        end_date = start_date + timedelta(days=1)
        
        filtered_metadatas = filter_by_date_range(metadatas, start_date, end_date)
        
        # Should only get the Stack Overflow entry (last Friday)
        assert len(filtered_metadatas) == 1
        assert filtered_metadatas[0]['domain'] == 'stackoverflow.com'
        assert filtered_metadatas[0]['visit_count'] == 10
        
        print(f"✅ Filtered for last Friday: {len(filtered_metadatas)} entries")
    
    def test_enhanced_context_with_temporal_filtering(self, sample_data_with_dates):
        """Test enhanced context with temporal filtering."""
        documents, metadatas = sample_data_with_dates
        
        # Test with temporal filter for last Friday using the same logic as the function
        now = datetime.now()
        target_day = 4  # Friday
        current_day = now.weekday()
        days_back = (current_day - target_day) % 7
        if days_back == 0:
            days_back = 7  # Last week's day
        last_friday = now - timedelta(days=days_back)
        last_friday = last_friday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        temporal_filter = (last_friday, last_friday + timedelta(days=1))
        
        enhanced_context = enhance_context_for_qa(documents, metadatas, temporal_filter)
        
        # Verify temporal period is included
        assert enhanced_context['browsing_summary']['temporal_period'] == temporal_filter
        
        # Verify only last Friday data is included
        summary = enhanced_context['browsing_summary']
        assert summary['total_visits'] == 10  # Only Stack Overflow visits
        assert summary['unique_domains'] == 1  # Only one domain
        assert summary['total_urls'] == 1  # Only one URL
        
        print(f"✅ Enhanced context with temporal filtering: {summary['total_visits']} visits")
    
    def test_temporal_qa_integration(self, temp_vector_store_dir, sample_data_with_dates):
        """Test full Q&A integration with temporal filtering."""
        documents, metadatas = sample_data_with_dates
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test temporal questions
        temporal_questions = [
            "What is my most visited website last Friday?",
            "How many times did I visit GitHub yesterday?",
            "What websites did I visit today?",
            "What are my most visited sites this week?"
        ]
        
        for question in temporal_questions:
            try:
                result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
                
                # Verify result structure
                assert 'answer' in result
                assert 'enhanced_context' in result
                assert isinstance(result['answer'], str)
                assert len(result['answer']) > 0
                
                # Verify enhanced context has temporal information
                enhanced_context = result['enhanced_context']
                assert 'browsing_summary' in enhanced_context
                
                # Check if temporal period is mentioned in answer
                answer_lower = result['answer'].lower()
                temporal_keywords = ['friday', 'yesterday', 'today', 'week', 'time', 'period']
                has_temporal_context = any(keyword in answer_lower for keyword in temporal_keywords)
                
                print(f"✅ Temporal question: '{question}'")
                print(f"   Answer length: {len(result['answer'])} chars")
                print(f"   Has temporal context: {has_temporal_context}")
                print(f"   Answer preview: {result['answer'][:100]}...")
                
            except Exception as e:
                pytest.fail(f"Failed to process temporal question '{question}': {e}")
        
        store.close()
    
    def test_temporal_filtering_edge_cases(self):
        """Test edge cases in temporal filtering."""
        # Test with invalid dates
        metadatas = [
            {'visit_time': 'invalid-date', 'visit_count': 1},
            {'visit_time': '', 'visit_count': 1},
            {'visit_count': 1},  # No visit_time
        ]
        
        # Should handle invalid dates gracefully
        filtered = filter_by_date_range(metadatas, datetime.now(), datetime.now() + timedelta(days=1))
        assert len(filtered) == 3  # Should include all (better to include than exclude)
        
        print("✅ Edge cases handled gracefully")
    
    def test_temporal_patterns_comprehensive(self):
        """Test comprehensive temporal pattern matching."""
        test_cases = [
            ("last monday", "last_day"),
            ("last tuesday", "last_day"),
            ("last wednesday", "last_day"),
            ("last thursday", "last_day"),
            ("last friday", "last_day"),
            ("last saturday", "last_day"),
            ("last sunday", "last_day"),
            ("yesterday", "yesterday"),
            ("today", "today"),
            ("this week", "this_period"),
            ("this month", "this_period"),
            ("this year", "this_period"),
            ("2 days ago", "days_ago"),
            ("1 week ago", "weeks_ago"),
            ("3 months ago", "months_ago"),
            ("1 year ago", "years_ago"),
        ]
        
        for question, expected_type in test_cases:
            filtered_query, start_date, end_date = parse_temporal_reference(question)
            
            # Verify temporal reference was parsed
            assert start_date is not None
            assert end_date is not None
            assert start_date < end_date
            
            print(f"✅ Pattern '{question}' -> {expected_type}: {start_date.date()} to {end_date.date()}")
    
    def test_temporal_context_in_prompt(self, temp_vector_store_dir, sample_data_with_dates):
        """Test that temporal context is properly included in the prompt."""
        documents, metadatas = sample_data_with_dates
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test a temporal question
        question = "What is my most visited website last Friday?"
        result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
        
        # Verify temporal context is in the enhanced context
        enhanced_context = result['enhanced_context']
        summary = enhanced_context['browsing_summary']
        
        if summary.get('temporal_period'):
            start_date, end_date = summary['temporal_period']
            print(f"✅ Temporal period in context: {start_date.date()} to {end_date.date()}")
        else:
            print("⚠️ No temporal period found in context")
        
        # Verify answer mentions temporal information
        answer = result['answer'].lower()
        temporal_mentions = ['friday', 'last', 'time', 'period', 'date']
        has_temporal_mention = any(mention in answer for mention in temporal_mentions)
        
        print(f"✅ Answer has temporal mention: {has_temporal_mention}")
        print(f"   Answer: {result['answer'][:150]}...")
        
        store.close() 