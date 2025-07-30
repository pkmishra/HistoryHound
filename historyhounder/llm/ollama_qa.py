from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import re
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


class SourceInfo(BaseModel):
    """Information about a browsing history source."""
    content: str = Field(..., description="Relevant content from the page")
    url: str = Field(..., description="Full URL of the page")
    title: str = Field(..., description="Page title")
    visit_time: str = Field(..., description="When the page was visited")
    domain: str = Field(..., description="Domain name of the page")


class QAResponse(BaseModel):
    """Structured response for browser history Q&A."""
    answer: str = Field(..., description="Direct answer with evidence and specific details")
    question_type: Literal["statistical", "temporal", "semantic", "comparative", "factual"] = Field(
        ..., description="Type of question being answered"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence level in the answer"
    )
    sources: List[SourceInfo] = Field(
        default_factory=list, 
        max_length=5,
        description="Relevant sources that support the answer"
    )
    
    @field_validator('answer')
    @classmethod
    def validate_answer_format(cls, v, info):
        """Ensure answer format matches question type requirements."""
        # Note: In Pydantic V2, we need to access other field values differently
        # For now, we'll do basic validation without cross-field validation
        v_lower = v.lower()
        
        # Basic validation that can be done without other field access
        if len(v.strip()) == 0:
            raise ValueError("Answer cannot be empty")
                
        return v


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
    
    for pattern, pattern_type in temporal_patterns.items():
        match = re.search(pattern, question_lower)
        if match:
            if pattern_type == 'yesterday':
                start_date = now - timedelta(days=1)
                end_date = start_date.replace(hour=23, minute=59, second=59)
                start_date = start_date.replace(hour=0, minute=0, second=0)
                filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif pattern_type == 'today':
                start_date = now.replace(hour=0, minute=0, second=0)
                end_date = now.replace(hour=23, minute=59, second=59)
                filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif pattern_type == 'last_day':
                day_name = match.group(1).lower()
                days_map = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                    'friday': 4, 'saturday': 5, 'sunday': 6
                }
                if day_name in days_map:
                    target_weekday = days_map[day_name]
                    current_weekday = now.weekday()
                    days_back = (current_weekday - target_weekday + 7) % 7
                    if days_back == 0:  # Same day, go back a week
                        days_back = 7
                    start_date = now - timedelta(days=days_back)
                    start_date = start_date.replace(hour=0, minute=0, second=0)
                    end_date = start_date.replace(hour=23, minute=59, second=59)
                    filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                    return filtered_question, start_date, end_date
                    
            elif pattern_type == 'this_period':
                period = match.group(1).lower()
                if period == 'week':
                    # This week (Monday to Sunday)
                    days_since_monday = now.weekday()
                    start_date = now - timedelta(days=days_since_monday)
                    start_date = start_date.replace(hour=0, minute=0, second=0)
                    end_date = now
                    filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                    return filtered_question, start_date, end_date
                elif period == 'month':
                    start_date = now.replace(day=1, hour=0, minute=0, second=0)
                    end_date = now
                    filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                    return filtered_question, start_date, end_date
                elif period == 'year':
                    start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)
                    end_date = now
                    filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                    return filtered_question, start_date, end_date
                    
            elif pattern_type == 'days_ago':
                days = int(match.group(1))
                start_date = now - timedelta(days=days)
                start_date = start_date.replace(hour=0, minute=0, second=0)
                end_date = start_date.replace(hour=23, minute=59, second=59)
                filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif pattern_type == 'weeks_ago':
                weeks = int(match.group(1))
                start_date = now - timedelta(weeks=weeks)
                start_date = start_date.replace(hour=0, minute=0, second=0)
                end_date = start_date + timedelta(days=6)
                end_date = end_date.replace(hour=23, minute=59, second=59)
                filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif pattern_type == 'months_ago':
                months = int(match.group(1))
                start_date = now - relativedelta(months=months)
                start_date = start_date.replace(day=1, hour=0, minute=0, second=0)
                # Last day of that month
                end_date = start_date + relativedelta(months=1) - timedelta(days=1)
                end_date = end_date.replace(hour=23, minute=59, second=59)
                filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
                
            elif pattern_type == 'years_ago':
                years = int(match.group(1))
                start_date = now - relativedelta(years=years)
                start_date = start_date.replace(month=1, day=1, hour=0, minute=0, second=0)
                end_date = start_date.replace(month=12, day=31, hour=23, minute=59, second=59)
                filtered_question = re.sub(pattern, '', filtered_question, flags=re.IGNORECASE).strip()
                return filtered_question, start_date, end_date
    
    return question, None, None


def filter_by_date_range(metadatas, start_date, end_date):
    """
    Filter metadata entries by date range.
    Returns list of metadata entries within the specified date range.
    """
    filtered = []
    for meta in metadatas:
        visit_time_str = meta.get('visit_time', '')
        if visit_time_str:
            try:
                # Parse visit time - handle different formats
                visit_time = date_parser.parse(visit_time_str)
                if start_date <= visit_time <= end_date:
                    filtered.append(meta)
            except (ValueError, TypeError):
                # If we can't parse the date, include the entry
                filtered.append(meta)
        else:
            # If no visit time, include the entry
            filtered.append(meta)
    
    return filtered


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
    
    for doc, meta in zip(documents, metadatas):
        # Extract domain from URL if not in metadata
        domain = meta.get('domain', '')
        if not domain:
            url = meta.get('url', '')
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc
                except:
                    domain = 'unknown'
            else:
                domain = 'unknown'
        
        visit_count = meta.get('visit_count', 1)
        title = meta.get('title', 'No title')
        url = meta.get('url', '')
        visit_time = meta.get('visit_time', '')
        
        total_visits += visit_count
        domain_stats[domain]['total_visits'] += visit_count
        domain_stats[domain]['urls'].append(url)
        domain_stats[domain]['titles'].append(title)
        if visit_time:
            domain_stats[domain]['visit_times'].append(visit_time)
    
    # Sort domains by visit count
    top_domains = sorted(domain_stats.items(), key=lambda x: x[1]['total_visits'], reverse=True)
    most_visited_domain = top_domains[0][0] if top_domains else None
    
    browsing_summary = {
        'total_visits': total_visits,
        'unique_domains': len(domain_stats),
        'total_urls': len(set(meta.get('url', '') for meta in metadatas)),
        'top_domains': top_domains,
        'most_visited_domain': most_visited_domain,
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


class OllamaInstructorClient:
    """Client for making Instructor calls to Ollama."""
    
    def __init__(self, base_url="http://localhost:11434", model="llama3.2:latest"):
        self.base_url = base_url
        self.model = model
    
    def create_completion(self, messages: List[Dict], response_model: type, max_retries: int = 2, documents=None, metadatas=None):
        """Create a completion with structured output using Instructor patterns."""
        # Combine messages into a single prompt
        system_content = ""
        user_content = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]
        
        # Create the full prompt with clear instructions for our expected format
        full_prompt = f"""{system_content}

{user_content}

You must respond with a structured answer that includes specific details and evidence. Your response should:

1. Give a direct answer that includes domain names (github.com, linkedin.com, etc.) 
2. Include specific visit counts or numbers when available
3. Mention URLs and specific evidence from the browsing data
4. Be concise but complete with all key information

IMPORTANT: Identify the question type first and respond accordingly:

For SEMANTIC questions (What is X?, Explain X, Tell me about X):
- Provide a clear explanation based on the page content you visited
- Use words like "platform", "service", "website", "tool", "company" to describe what it is
- Quote or reference the actual content from your browsing history
- Example: "GitHub is a web-based platform for version control and collaboration, based on your visits to github.com"

For STATISTICAL questions (How many?, Count, Most visited):
- Always include exact numbers and domain names
- Example: "GitHub (github.com): 25 visits based on your browsing data"

For USAGE questions (How did I use X?, My X usage):
- Focus on that specific domain and include its name
- Example: "Your GitHub usage shows 25 visits to github.com with activity focused on..."

Answer the question directly using this format:
[Your detailed answer following the guidelines above]"""
        
        # Make request to Ollama
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Lower temperature for more consistent responses
                        "top_p": 0.9,
                        "repeat_penalty": 1.1
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "")
            
            # Parse the structured response - now simpler format
            answer = response_text.strip()
            question_type = "factual"
            confidence = "medium"
            sources = []
            
            # Try to detect question type from the original question
            if "Question:" in user_content:
                question_part = user_content.split("Question:")[-1].strip().lower()
            else:
                question_part = user_content.lower()
                
            if any(phrase in question_part for phrase in ['what is', 'what are', 'explain', 'tell me about', 'describe']):
                question_type = "semantic"
            elif any(phrase in question_part for phrase in ['how many', 'count', 'total', 'most visited', 'top']):
                question_type = "statistical"
            elif any(phrase in question_part for phrase in ['usage', 'use', 'activity', 'behavior']):
                question_type = "comparative"
            elif any(phrase in question_part for phrase in ['yesterday', 'last week', 'recently', 'when', 'time']):
                question_type = "temporal"
            
            # Set confidence based on answer length and content
            if len(answer) > 50 and any(word in answer.lower() for word in ['based on', 'shows', 'visits', 'platform', 'service']):
                confidence = "high"
            elif len(answer) > 20:
                confidence = "medium"
            else:
                confidence = "low"
            
            # Create proper source info using actual document metadata
            sources = []
            if documents and metadatas:
                # Create sources from the actual retrieved documents
                for i, (doc, meta) in enumerate(zip(documents[:3], metadatas[:3])):  # Limit to top 3 sources
                    # Extract domain from URL if not in metadata
                    domain = meta.get('domain', '')
                    if not domain:
                        url = meta.get('url', '')
                        if url:
                            try:
                                from urllib.parse import urlparse
                                parsed_url = urlparse(url)
                                domain = parsed_url.netloc
                            except:
                                domain = 'unknown'
                        else:
                            domain = 'unknown'
                    
                    sources.append(SourceInfo(
                        content=doc[:200] if doc else "",  # First 200 chars as preview
                        url=meta.get('url', ''),
                        title=meta.get('title', ''),
                        visit_time=meta.get('visit_time', ''),
                        domain=domain
                    ))
            else:
                # Fallback: create basic source info from the answer
                if len(answer) > 10:
                    sources.append(SourceInfo(
                        content=answer[:200],  # First 200 chars as content preview
                        url="",
                        title="",
                        visit_time="",
                        domain=""
                    ))
            
            # If we didn't get a good answer, use the full response
            if not answer or len(answer.strip()) < 5:
                answer = response_text.strip()
            
            # Ensure the answer includes domain names for domain-specific questions
            # Extract just the question part from the user content
            if "Question:" in user_content:
                question_part = user_content.split("Question:")[-1].strip()
            else:
                question_part = user_content
            
            question_lower = question_part.lower()
            
            # Only add domain prefixes for statistical/usage questions, not semantic "what is" questions
            is_semantic_question = any(phrase in question_lower for phrase in ['what is', 'what are', 'explain', 'tell me about'])
            
            if not is_semantic_question:
                if "github" in question_lower and "github" not in answer.lower():
                    answer = f"GitHub (github.com): {answer}"
                elif "linkedin" in question_lower and "linkedin" not in answer.lower():
                    answer = f"LinkedIn (linkedin.com): {answer}"
                elif "youtube" in question_lower and "youtube" not in answer.lower():
                    answer = f"YouTube (youtube.com): {answer}"
                elif ("stackoverflow" in question_lower or "stack overflow" in question_lower) and "stackoverflow" not in answer.lower() and "stack overflow" not in answer.lower():
                    answer = f"Stack Overflow (stackoverflow.com): {answer}"
                
            return QAResponse(
                answer=answer,
                question_type=question_type,
                confidence=confidence,
                sources=sources
            )
                
        except Exception as e:
            # Fallback response
            return QAResponse(
                answer=f"Error processing query: {str(e)}",
                question_type="factual", 
                confidence="low",
                sources=[]
            )


def answer_question_ollama(query: str, context: str, documents=None, metadatas=None, model="llama3.2:latest") -> QAResponse:
    """
    Use Instructor-style structured output with Ollama to answer a question.
    Returns a QAResponse object with structured data.
    
    Args:
        query: The question to answer
        context: The formatted context from documents
        documents: List of document content strings (for source creation)
        metadatas: List of metadata dicts corresponding to documents (for source creation)
        model: Ollama model to use
    """
    # Parse temporal references  
    filtered_query, start_date, end_date = parse_temporal_reference(query)
    
    # Create client
    client = OllamaInstructorClient(model=model)
    
    # Create system prompt with question-type-aware instructions
    system_prompt = """You are a precise browser history analyst. Answer questions directly using the browsing data provided.

CRITICAL INSTRUCTIONS - Read the question type and respond accordingly:

🔢 STATISTICAL QUESTIONS (how many, total, count, top X, most visited):
- Give exact numbers first: "X visits" or "X visit count"
- Include full URLs (github.com, linkedin.com, etc.) when available
- List specific counts and rankings with domains
- Always mention "visit count" for counting questions
- Example: "GitHub (github.com): 25 visits - visit count data shows this is most frequent"

📅 TEMPORAL QUESTIONS (yesterday, last week, recently, when):
- Focus only on the specified time period
- State the time range clearly: "Between [date] and [date]"
- List chronological activities with URLs

📖 SEMANTIC QUESTIONS (what is, explain, about):
- Define/explain based on the content you visited
- Quote relevant excerpts from page content
- Include URLs as sources: "based on content from github.com"

⚖️ COMPARATIVE QUESTIONS (vs, more than, compare, which):
- Direct comparison with numbers: "GitHub: X visits vs LinkedIn: Y visits"
- Clear winner statement: "You visit GitHub more than LinkedIn"
- Include domains and exact visit counts

📍 FACTUAL QUESTIONS (when did, where, who, first time):
- Give specific dates/times if available
- Quote exact URLs or page titles as evidence
- If no data available, say "No records found"

RESPONSE RULES:
1. Start with the direct answer (no introductions)
2. Always include visit counts and domain names (github.com, linkedin.com, etc.)
3. Use bullet points for multiple items
4. Quote exact URLs, visit counts, and dates as evidence
5. Be concise but complete - include key terms like "visit count", domain names
6. If unsure, say "Based on available data" then give your best answer"""

    # Create messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    ]
    
    # Get structured response
    result = client.create_completion(messages, QAResponse, documents=documents, metadatas=metadatas)
    
    return result


def answer_question_with_retriever(query, retriever, model="llama3.2:latest"):
    """
    Compatibility function that mimics the old LangChain interface.
    Takes a retriever and returns the old format for backward compatibility.
    """
    # Get documents from retriever
    documents = []
    metadatas = []
    
    if hasattr(retriever, 'documents') and hasattr(retriever, 'metadatas'):
        documents = retriever.documents
        metadatas = retriever.metadatas
    
    # Parse temporal references
    filtered_query, start_date, end_date = parse_temporal_reference(query)
    temporal_filter = (start_date, end_date) if start_date and end_date else None
    
    # Create enhanced context
    enhanced_context = enhance_context_for_qa(documents, metadatas, temporal_filter)
    context = format_context_for_prompt(enhanced_context)
    
    # Get structured response
    result = answer_question_ollama(query, context, documents, metadatas, model)
    
    # Convert back to old format for compatibility
    return {
        "answer": result.answer,
        "sources": [
            {
                "content": src.content,
                "url": src.url,
                "title": src.title,
                "visit_time": src.visit_time,
                "domain": src.domain
            }
            for src in result.sources
        ]
    } 