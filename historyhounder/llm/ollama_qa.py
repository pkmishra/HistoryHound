from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from datetime import datetime
from collections import defaultdict
import re


def enhance_context_for_qa(documents, metadatas):
    """
    Create rich context with aggregated statistics and insights.
    """
    if not documents or not metadatas:
        return {
            'browsing_summary': {
                'total_visits': 0,
                'unique_domains': 0,
                'total_urls': 0,
                'top_domains': [],
                'most_visited_domain': None
            },
            'domain_stats': {},
            'documents': documents,
            'metadatas': metadatas
        }
    
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
        'most_visited_domain': top_domains[0] if top_domains else None
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
        
        docs_text += f"{i}. {title}\n"
        docs_text += f"   URL: {url}\n"
        docs_text += f"   Domain: {domain}\n"
        docs_text += f"   Visits: {visits}\n"
        docs_text += f"   Content: {doc[:200]}{'...' if len(doc) > 200 else ''}\n\n"
    
    return summary_text + docs_text


def answer_question_ollama(query, retriever, model="llama3.2:latest"):
    """
    Use LangChain RetrievalQA with Ollama as the LLM to answer a question given a retriever.
    Returns a dict with 'answer' and 'sources'.
    """
    llm = OllamaLLM(model=model)
    
    # Enhanced prompt template
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are an expert browser history analyst with access to detailed browsing data. You can analyze visit patterns, content, and provide insights about browsing behavior.

{context}

ANALYSIS INSTRUCTIONS:
- For statistical questions (counts, totals, rankings): Provide exact numbers, percentages, and rankings
- For trend questions (patterns, changes over time): Identify patterns, frequency changes, and insights
- For comparative questions (comparing different things): Show side-by-side analysis with metrics
- For semantic questions (content meaning): Explain what the content is about and its context
- For domain-specific questions: Focus on specific websites/domains with visit details
- Always cite visit counts, URLs, and timestamps as evidence
- Provide structured, clear answers with supporting data

Question: {question}

Provide a comprehensive answer with:
1. Direct answer to the question with specific data
2. Supporting evidence (visit counts, URLs, timestamps)
3. Relevant insights and patterns
4. Clear structure and formatting

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
        "sources": [doc.page_content for doc in result["source_documents"]],
    } 