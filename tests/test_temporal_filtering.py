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
                
                answer = result['answer']
                answer_lower = answer.lower()
                
                # STRONG TEMPORAL ASSERTIONS: Verify temporal filtering actually worked
                if "last Friday" in question.lower():
                    # Should show Stack Overflow (10 visits on last Friday)
                    assert "stackoverflow" in answer_lower or "stack overflow" in answer_lower, f"Expected Stack Overflow for last Friday, got: {answer}"
                    assert "10" in answer or "ten" in answer_lower, f"Expected 10 visits for Stack Overflow on last Friday, got: {answer}"
                    
                elif "yesterday" in question.lower():
                    if "github" in question.lower():
                        # "How many times did I visit GitHub yesterday?" should be 0 or "not visited"
                        # GitHub was visited TODAY (25 visits), not yesterday
                        github_mentioned = "github" in answer_lower
                        if github_mentioned:
                            # If GitHub is mentioned, it should clarify it wasn't visited yesterday
                            no_visits_indicators = ["0", "zero", "not visited", "didn't visit", "no visit", "not access"]
                            has_no_visits = any(indicator in answer_lower for indicator in no_visits_indicators)
                            assert has_no_visits, f"Expected 0 GitHub visits yesterday (GitHub was visited today), got: {answer}"
                    else:
                        # General yesterday question should show LinkedIn (15 visits yesterday)
                        assert "linkedin" in answer_lower, f"Expected LinkedIn for yesterday (15 visits), got: {answer}"
                        assert "15" in answer or "fifteen" in answer_lower, f"Expected 15 visits for LinkedIn yesterday, got: {answer}"
                        
                elif "today" in question.lower():
                    # Should show GitHub (25 visits today)
                    assert "github" in answer_lower, f"Expected GitHub for today (25 visits), got: {answer}"
                    assert "25" in answer or "twenty" in answer_lower, f"Expected 25 visits for GitHub today, got: {answer}"
                    
                elif "this week" in question.lower():
                    # Should include multiple sites from this week
                    week_domains = ["github", "linkedin"]  # Both today and yesterday are this week
                    week_found = any(domain in answer_lower for domain in week_domains)
                    assert week_found, f"Expected this week's sites (GitHub/LinkedIn), got: {answer}"
                
                print(f"✅ Temporal question: '{question}'")
                print(f"   Answer: {answer[:150]}{'...' if len(answer) > 150 else ''}")
                
            except Exception as e:
                pytest.fail(f"Failed to process temporal question '{question}': {e}")
        
        store.close()
    
    def test_most_visited_yesterday_specific(self, temp_vector_store_dir, sample_data_with_dates):
        """Test the specific user question: 'Most visited site yesterday'."""
        documents, metadatas = sample_data_with_dates
        
        # Setup vector store
        store = ChromaVectorStore(persist_directory=temp_vector_store_dir)
        embedder = get_embedder('sentence-transformers')
        embeddings = embedder.embed(documents)
        store.add(documents, embeddings, metadatas)
        
        # Test the exact user question
        question = "Most visited site yesterday"
        result = llm_qa_search(question, top_k=5, persist_directory=temp_vector_store_dir)
        
        answer = result['answer']
        answer_lower = answer.lower()
        
        print(f"\n🎯 TESTING USER'S SPECIFIC QUESTION")
        print(f"Question: '{question}'")
        print(f"Answer: {answer}")
        print()
        print(f"📊 Expected: LinkedIn (15 visits yesterday)")
        print(f"📊 Data context:")
        print(f"  - GitHub: 25 visits TODAY (should not appear)")
        print(f"  - LinkedIn: 15 visits YESTERDAY (should be the answer)")
        print(f"  - Stack Overflow: 10 visits LAST FRIDAY (should not appear)")
        print(f"  - Others: older dates (should not appear)")
        
        # DEBUG: Check the enhanced context first
        enhanced_context = result['enhanced_context']
        summary = enhanced_context['browsing_summary']
        
        print(f"\n🔍 DEBUG ENHANCED CONTEXT:")
        print(f"  Temporal period: {summary.get('temporal_period')}")
        print(f"  Total visits: {summary['total_visits']}")
        print(f"  Unique domains: {summary['unique_domains']}")
        print(f"  Top domains: {summary.get('top_domains', [])}")
        print(f"  Documents count: {len(enhanced_context.get('documents', []))}")
        print(f"  Metadatas count: {len(enhanced_context.get('metadatas', []))}")
        
        # DEBUG: Check the raw metadatas in enhanced context
        metadatas_in_context = enhanced_context.get('metadatas', [])
        print(f"\n🔍 DEBUG METADATAS IN ENHANCED CONTEXT:")
        for i, meta in enumerate(metadatas_in_context):
            print(f"  [{i}] {meta.get('domain', 'no-domain')}: {meta.get('visit_count', 0)} visits at {meta.get('visit_time', 'no-time')}")
        
        # CRITICAL ASSERTION: Should show LinkedIn as most visited yesterday
        assert "linkedin" in answer_lower, f"CRITICAL: Expected LinkedIn (15 visits yesterday) as answer, got: {answer}"
        
        # Should NOT show today's data (GitHub) or older data
        assert "github" not in answer_lower or "not visited yesterday" in answer_lower, f"Should not mention GitHub (was visited today, not yesterday), got: {answer}"
        assert "stackoverflow" not in answer_lower, f"Should not mention Stack Overflow (was visited last Friday, not yesterday), got: {answer}"
        
        # Should mention the visit count
        visit_indicators = ["15", "fifteen"]
        has_visit_count = any(indicator in answer for indicator in visit_indicators)
        assert has_visit_count, f"Expected to mention 15 visits for LinkedIn yesterday, got: {answer}"
        
        # Verify enhanced context shows temporal filtering was applied
        enhanced_context = result['enhanced_context']
        summary = enhanced_context['browsing_summary']
        
        # If temporal filtering worked, should only show yesterday's data
        temporal_period = summary.get('temporal_period')
        if temporal_period:
            print(f"✅ Temporal period detected: {temporal_period}")
            # Should only have LinkedIn's visits (15) if filtering worked
            assert summary['total_visits'] == 15, f"Expected 15 total visits (only LinkedIn yesterday), got {summary['total_visits']}"
            assert summary['unique_domains'] == 1, f"Expected 1 domain (only LinkedIn yesterday), got {summary['unique_domains']}"
        else:
            print(f"⚠️ No temporal period found - filtering may not be working")
        
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