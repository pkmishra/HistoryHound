from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from datetime import datetime, timedelta
from collections import defaultdict
import re
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


def parse_temporal_reference(question):
    """
    Parse temporal references from questions like 'last Friday', 'yesterday', 'this week'.
    Returns (filtered_question, start_date, end_date) or (question, None, None) if no temporal reference.
    """
    question_lower = question.lower()
    
    # Common temporal patterns
    temporal_patterns = {
        r'last (\w+)': 'last_day',
        r'yesterday': 'yesterday', 
        r'today': 'today',
        r'this (\w+)': 'this_period',
        r'(\d+) days? ago': 'days_ago',
        r'(\d+) weeks? ago': 'weeks_ago',
        r'(\d+) months? ago': 'months_ago',
        r'(\d+) years? ago': 'years_ago'
    }
    
    now = datetime.now()
    filtered_question = question
    
    for pattern, ref_type in temporal_patterns.items():
        match = re.search(pattern, question_lower)
        if match:
            if ref_type == 'last_day':
                day_name = match.group(1)
                # Map day names to weekday numbers (Monday=0, Sunday=6)
                day_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                          'friday': 4, 'saturday': 5, 'sunday': 6}
                if day_name in day_map:
                    target_day = day_map[day_name]
                    current_day = now.weekday()
                    
                    # Calculate days back to last occurrence of target day
                    days_back = (current_day - target_day) % 7
                    if days_back == 0:
                        days_back = 7  # Last week's day
                    
                    start_date = now - timedelta(days=days_back)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=1)
                    
                    filtered_question = re.sub(pattern, '', question_lower, flags=re.IGNORECASE).strip()
                    return filtered_question, start_date, end_date
                    
            elif ref_type == 'yesterday':
                start_date = now - timedelta(days=1)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
                filtered_question = re.sub(r'yesterday', '', question_lower, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif ref_type == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
                filtered_question = re.sub(r'today', '', question_lower, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif ref_type == 'this_period':
                period = match.group(1)
                if period in ['week', 'month', 'year']:
                    if period == 'week':
                        start_date = now - timedelta(days=now.weekday())
                        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        end_date = start_date + timedelta(days=7)
                    elif period == 'month':
                        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                        end_date = (start_date + relativedelta(months=1))
                    elif period == 'year':
                        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                        end_date = start_date.replace(year=start_date.year + 1)
                    filtered_question = re.sub(pattern, '', question_lower, flags=re.IGNORECASE).strip()
                    return filtered_question, start_date, end_date
                    
            elif ref_type in ['days_ago', 'weeks_ago', 'months_ago', 'years_ago']:
                amount = int(match.group(1))
                if ref_type == 'days_ago':
                    start_date = now - timedelta(days=amount)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=1)
                elif ref_type == 'weeks_ago':
                    start_date = now - timedelta(weeks=amount)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=7)
                elif ref_type == 'months_ago':
                    start_date = now - relativedelta(months=amount)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + relativedelta(months=1)
                elif ref_type == 'years_ago':
                    start_date = now - relativedelta(years=amount)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + relativedelta(years=1)
                filtered_question = re.sub(pattern, '', question_lower, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
    
    return question, None, None


def filter_by_date_range(metadatas, start_date, end_date):
    """
    Filter metadata by date range.
    """
    if not start_date or not end_date:
        return metadatas
    
    filtered_metadatas = []
    for meta in metadatas:
        visit_time_str = meta.get('visit_time', '')
        if visit_time_str:
            try:
                # Try to parse the visit time
                if isinstance(visit_time_str, str):
                    visit_time = date_parser.parse(visit_time_str)
                else:
                    visit_time = visit_time_str
                
                # Check if visit time is within the range
                if start_date <= visit_time < end_date:
                    filtered_metadatas.append(meta)
            except (ValueError, TypeError):
                # If we can't parse the date, include it (better to include than exclude)
                filtered_metadatas.append(meta)
        else:
            # If no visit time, include it
            filtered_metadatas.append(meta)
    
    return filtered_metadatas


def enhance_context_for_qa(documents, metadatas, temporal_filter=None):
    """
    Create rich context with aggregated statistics and insights.
    temporal_filter: tuple of (start_date, end_date) for temporal filtering
    """
    if not documents or not metadatas:
        return {
            'browsing_summary': {
                'total_visits': 0,
                'unique_domains': 0,
                'total_urls': 0,
                'top_domains': [],
                'most_visited_domain': None,
                'temporal_period': None
            },
            'domain_stats': {},
            'documents': documents,
            'metadatas': metadatas
        }
    
    # Apply temporal filtering if provided
    if temporal_filter:
        start_date, end_date = temporal_filter
        filtered_metadatas = filter_by_date_range(metadatas, start_date, end_date)
        # Get corresponding documents
        filtered_documents = []
        for meta in filtered_metadatas:
            try:
                idx = metadatas.index(meta)
                filtered_documents.append(documents[idx])
            except ValueError:
                continue
        documents = filtered_documents
        metadatas = filtered_metadatas
    
    # Aggregate statistics
    total_visits = 0
    domain_stats = defaultdict(lambda: {
        'total_visits': 0,
        'urls': [],
        'titles': [],
        'visit_times': []
    })
    
    # Process each document
    for doc, meta in zip(documents, metadatas):
        visits = meta.get('visit_count', 1)
        total_visits += visits
        domain = meta.get('domain', '')
        url = meta.get('url', '')
        title = meta.get('title', '')
        visit_time = meta.get('visit_time', '')
        
        if domain:
            domain_stats[domain]['total_visits'] += visits
            domain_stats[domain]['urls'].append(url)
            domain_stats[domain]['titles'].append(title)
            if visit_time:
                domain_stats[domain]['visit_times'].append(visit_time)
    
    # Sort domains by visit count
    top_domains = sorted(
        domain_stats.items(), 
        key=lambda x: x[1]['total_visits'], 
        reverse=True
    )[:10]
    
    # Create browsing summary
    browsing_summary = {
        'total_visits': total_visits,
        'unique_domains': len(domain_stats),
        'total_urls': len(documents),
        'top_domains': top_domains,
        'most_visited_domain': top_domains[0] if top_domains else None,
        'temporal_period': temporal_filter
    }
    
    return {
        'browsing_summary': browsing_summary,
        'domain_stats': dict(domain_stats),
        'documents': documents,
        'metadatas': metadatas
    }


def format_context_for_prompt(enhanced_context):
    """
    Format the enhanced context into a readable prompt section.
    """
    summary = enhanced_context['browsing_summary']
    domain_stats = enhanced_context['domain_stats']
    documents = enhanced_context['documents']
    metadatas = enhanced_context['metadatas']
    
    # Format browsing summary
    summary_text = f"""
BROWSING SUMMARY:
- Total visits: {summary['total_visits']}
- Unique domains: {summary['unique_domains']}
- Total URLs: {summary['total_urls']}
"""
    
    # Add temporal period if specified
    if summary.get('temporal_period'):
        start_date, end_date = summary['temporal_period']
        summary_text += f"- Time period: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n"
    
    # Format top domains
    if summary['top_domains']:
        summary_text += "\nTOP DOMAINS BY VISITS:\n"
        for i, (domain, stats) in enumerate(summary['top_domains'][:5], 1):
            summary_text += f"{i}. {domain}: {stats['total_visits']} visits\n"
    
    # Format relevant documents
    docs_text = "\nRELEVANT DOCUMENTS:\n"
    for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
        title = meta.get('title', 'No title')
        url = meta.get('url', 'No URL')
        visits = meta.get('visit_count', 1)
        domain = meta.get('domain', '')
        visit_time = meta.get('visit_time', '')
        
        docs_text += f"{i}. {title}\n"
        docs_text += f"   URL: {url}\n"
        docs_text += f"   Domain: {domain}\n"
        docs_text += f"   Visits: {visits}\n"
        if visit_time:
            docs_text += f"   Visit time: {visit_time}\n"
        docs_text += f"   Content: {doc[:200]}{'...' if len(doc) > 200 else ''}\n\n"
    
    return summary_text + docs_text


def answer_question_ollama(query, retriever, model="llama3.2:latest"):
    """
    Use LangChain RetrievalQA with Ollama as the LLM to answer a question given a retriever.
    Returns a dict with 'answer' and 'sources'.
    """
    llm = OllamaLLM(model=model)
    
    # Parse temporal references
    filtered_query, start_date, end_date = parse_temporal_reference(query)
    temporal_filter = (start_date, end_date) if start_date and end_date else None
    
    # Enhanced prompt template with temporal support
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are an expert browser history analyst with access to detailed browsing data. You can analyze visit patterns, content, and provide insights about browsing behavior.

{context}

ANALYSIS INSTRUCTIONS:
- For statistical questions (counts, totals, rankings): Provide exact numbers, percentages, and rankings
- For temporal questions (last Friday, yesterday, this week): Focus on the specified time period and mention the time range
- For trend questions (patterns, changes over time): Identify patterns, frequency changes, and insights
- For comparative questions (comparing different things): Show side-by-side analysis with metrics
- For semantic questions (content meaning): Explain what the content is about and its context
- For domain-specific questions: Focus on specific websites/domains with visit details
- Always cite visit counts, URLs, and timestamps as evidence
- Provide structured, clear answers with supporting data
- If a time period is specified, clearly state the time range in your answer

Question: {question}

Provide a comprehensive answer with:
1. Direct answer to the question with specific data
2. Supporting evidence (visit counts, URLs, timestamps)
3. Relevant insights and patterns
4. Clear structure and formatting
5. Time period context if applicable

Answer:
"""
    )
    
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    result = qa.invoke({"query": query})
    return {
        "answer": result["result"],
        "sources": [
            {
                "content": doc.page_content,
                "url": doc.metadata.get("url", ""),
                "title": doc.metadata.get("title", ""),
                "visit_time": doc.metadata.get("visit_time", ""),
                "domain": doc.metadata.get("domain", "")
            }
            for doc in result["source_documents"]
        ],
    } 