#!/usr/bin/env python3
"""
HistoryHounder Backend Server
Provides API endpoints for the browser extension to access HistoryHounder functionality
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# FastAPI imports
from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from .search import semantic_search, llm_qa_search
    from .extract_chrome_history import extract_history_from_sqlite
    from .pipeline import extract_and_process_history
    from .vector_store import ChromaVectorStore
    HISTORYHOUNDER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: HistoryHounder not available: {e}")
    HISTORYHOUNDER_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_MODEL = os.getenv("HISTORYHOUNDER_OLLAMA_MODEL", "llama3.2:latest")
# Allow tests to override the vector store directory
VECTOR_STORE_DIR = os.getenv("HISTORYHOUNDER_VECTOR_STORE_DIR", "chroma_db")
# Allow tests to override the history database directory
HISTORY_DB_DIR = os.getenv("HISTORYHOUNDER_HISTORY_DB_DIR", "history_db")

# Pydantic Models for API
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Server status")
    historyhounder_available: bool = Field(..., description="Whether HistoryHounder backend is available")
    version: str = Field(..., description="API version")
    ollama_model: str = Field(..., description="Configured Ollama model")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results to return")

class SearchResult(BaseModel):
    """Search result model"""
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    content: str = Field(default="", description="Page content")
    visit_time: Optional[str] = Field(None, description="Visit timestamp")
    domain: str = Field(default="", description="Domain name")
    distance: float = Field(..., description="Semantic similarity score")

class SearchResponse(BaseModel):
    """Search response model"""
    success: bool = Field(..., description="Request success status")
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class SourceInfo(BaseModel):
    """Source information model for Q&A responses"""
    content: str = Field(..., description="Source document content")
    url: str = Field(default="", description="Source URL")
    title: str = Field(default="", description="Source title")
    visit_time: str = Field(default="", description="Visit timestamp")
    domain: str = Field(default="", description="Domain name")

class QaRequest(BaseModel):
    """Q&A request model"""
    question: str = Field(..., min_length=1, description="Question to ask")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context items")

class QaResponse(BaseModel):
    """Q&A response model"""
    success: bool = Field(..., description="Request success status")
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="AI-generated answer")
    sources: List[SourceInfo] = Field(default=[], description="Source documents with metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class HistoryItem(BaseModel):
    """Browser history item model"""
    id: str = Field(..., description="History item ID")
    url: str = Field(..., description="Page URL")
    title: str = Field(..., description="Page title")
    lastVisitTime: int = Field(..., description="Last visit timestamp (microseconds)")
    visitCount: int = Field(default=1, description="Number of visits")

class ProcessHistoryRequest(BaseModel):
    """History processing request model"""
    history: List[HistoryItem] = Field(..., description="Browser history items")

class ProcessHistoryResponse(BaseModel):
    """History processing response model"""
    success: bool = Field(..., description="Request success status")
    processed_count: int = Field(..., description="Number of items processed")
    message: str = Field(..., description="Processing status message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class StatsResponse(BaseModel):
    """Statistics response model"""
    success: bool = Field(..., description="Request success status")
    stats: Dict[str, Any] = Field(..., description="Vector store statistics")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

# Create FastAPI app
app = FastAPI(
    title="HistoryHounder API",
    description="API for HistoryHounder browser extension integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Custom CORS middleware to ensure headers are always present
class CORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

# Add CORS middleware
app.add_middleware(CORSMiddleware)

# API Endpoints
@app.options("/api/health")
async def options_health():
    """Handle OPTIONS requests for health endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.options("/api/search")
async def options_search():
    """Handle OPTIONS requests for search endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.options("/api/qa")
async def options_qa():
    """Handle OPTIONS requests for Q&A endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.options("/api/process-history")
async def options_process_history():
    """Handle OPTIONS requests for process-history endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.options("/api/stats")
async def options_stats():
    """Handle OPTIONS requests for stats endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check server health and HistoryHounder availability",
    tags=["System"]
)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        historyhounder_available=HISTORYHOUNDER_AVAILABLE,
        version="1.0.0",
        ollama_model=OLLAMA_MODEL
    )

@app.get(
    "/api/search",
    response_model=SearchResponse,
    summary="Semantic Search",
    description="Perform semantic search on browser history",
    responses={
        200: {"description": "Search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        503: {"model": ErrorResponse, "description": "HistoryHounder backend unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Search"]
)
async def search_history(
    q: str = Query(..., description="Search query", min_length=1),
    top_k: int = Query(default=5, ge=1, le=100, description="Number of results to return")
):
    """Perform semantic search on browser history"""
    try:
        if not HISTORYHOUNDER_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="HistoryHounder backend not available"
            )
        
        # Perform semantic search
        results = semantic_search(q, top_k=top_k)
        
        # Format results for API
        formatted_results = []
        for result in results:
            # Format visit_time if it exists
            visit_time = result.get('visit_time', '')
            if visit_time:
                if isinstance(visit_time, datetime):
                    visit_time = visit_time.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(visit_time, str):
                    # If it's already a string, try to parse and format it
                    try:
                        dt = datetime.fromisoformat(visit_time.replace('Z', '+00:00'))
                        visit_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass  # Keep original if parsing fails
            
            formatted_results.append(SearchResult(
                title=result.get('title', 'Untitled'),
                url=result.get('url', ''),
                content=result.get('document', ''),
                visit_time=visit_time,
                domain=result.get('domain', ''),
                distance=result.get('distance', 0.0)
            ))
        
        return SearchResponse(
            success=True,
            query=q,
            results=formatted_results,
            total=len(formatted_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.post(
    "/api/qa",
    response_model=QaResponse,
    summary="AI Q&A",
    description="Ask AI questions about browser history",
    responses={
        200: {"description": "Q&A completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        503: {"model": ErrorResponse, "description": "HistoryHounder backend unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["Q&A"]
)
async def ask_question(request: QaRequest):
    """Ask AI questions about browser history"""
    try:
        if not HISTORYHOUNDER_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="HistoryHounder backend not available"
            )
        
        # Perform Q&A search
        result = llm_qa_search(request.question, top_k=request.top_k)
        
        # Format sources for the response
        sources = []
        for source in result.get('sources', []):
            sources.append(SourceInfo(
                content=source.get('content', ''),
                url=source.get('url', ''),
                title=source.get('title', ''),
                visit_time=source.get('visit_time', ''),
                domain=source.get('domain', '')
            ))
        
        return QaResponse(
            success=True,
            question=request.question,
            answer=result['answer'],
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Q&A error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Q&A failed: {str(e)}"
        )

@app.post(
    "/api/process-history",
    response_model=ProcessHistoryResponse,
    summary="Process History",
    description="Process browser history data through HistoryHounder pipeline",
    responses={
        200: {"description": "History processed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        503: {"model": ErrorResponse, "description": "HistoryHounder backend unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["History"]
)
async def process_history(request: ProcessHistoryRequest):
    """Process browser history data"""
    try:
        if not request.history or len(request.history) == 0:
            raise HTTPException(
                status_code=400,
                detail="History data is required"
            )
        
        if not HISTORYHOUNDER_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="HistoryHounder backend not available"
            )
        
        # Convert to format expected by pipeline
        history_data = [
            {
                'id': item.id,
                'url': item.url,
                'title': item.title,
                'lastVisitTime': item.lastVisitTime,
                'visitCount': item.visitCount
            }
            for item in request.history
        ]
        
        # Process history data through HistoryHounder pipeline
        try:
            # Import required modules
            from .content_fetcher import fetch_and_extract
            from .embedder import get_embedder
            from .vector_store import ChromaVectorStore
            from .utils import convert_metadata_for_chroma
            import tempfile
            import sqlite3
            from datetime import datetime
            
            # Create a persistent SQLite database from the extension data
            import os
            db_dir = HISTORY_DB_DIR
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, 'extension_history.sqlite')
            
            # Create the SQLite database with Chrome-compatible schema
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create the urls table (Chrome-compatible schema) if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT,
                    visit_count INTEGER,
                    typed_count INTEGER,
                    last_visit_time INTEGER,
                    hidden INTEGER DEFAULT 0
                )
            ''')
            
            # Insert the history data
            for item in history_data:
                # Chrome history API returns timestamps in milliseconds since Unix epoch
                chrome_time = item['lastVisitTime']
                
                # Convert from milliseconds since Unix epoch to seconds for SQLite storage
                unix_milliseconds = chrome_time
                
                # Validate timestamp bounds to prevent SQLite overflow
                if unix_milliseconds < 0 or unix_milliseconds > 9999999999999:  # Reasonable bounds
                    logger.warning(f"Invalid timestamp value: {unix_milliseconds}, using current time")
                    unix_milliseconds = int(datetime.now().timestamp() * 1000)
                
                # Convert to Unix timestamp (seconds since epoch) for SQLite storage
                # This avoids the very large Chrome microseconds format that can overflow SQLite INTEGER
                unix_seconds = unix_milliseconds // 1000
                
                cursor.execute('''
                    INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item['url'],
                    item['title'],
                    item['visitCount'],
                    0,  # typed_count
                    unix_seconds,
                    0   # hidden
                ))
            
            conn.commit()
            conn.close()
            
            # Now process through the HistoryHounder pipeline with incremental processing
            from .pipeline import extract_and_process_history
            
            # Get existing URLs from vector store to avoid reprocessing
            store = ChromaVectorStore(persist_directory=VECTOR_STORE_DIR)
            existing_count = store.count()
            logger.info(f"Current vector store count: {existing_count}")
            
            # Get existing URLs from the vector store
            existing_urls = set()
            if existing_count > 0:
                try:
                    # Get all documents to extract URLs
                    results = store.collection.get(include=['metadatas'])
                    if results and results['metadatas']:
                        existing_urls = {meta.get('url', '') for meta in results['metadatas'] if meta.get('url')}
                        logger.info(f"Found {len(existing_urls)} existing URLs in vector store")
                except Exception as e:
                    logger.warning(f"Could not get existing URLs: {e}")
            
            store.close()
            
            # Create a temporary database with only the current request URLs
            import tempfile
            temp_db_path = tempfile.mktemp(suffix='.sqlite')
            
            # Create the temporary SQLite database with Chrome-compatible schema
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            # Create the urls table (Chrome-compatible schema)
            cursor.execute('''
                CREATE TABLE urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT,
                    visit_count INTEGER,
                    typed_count INTEGER,
                    last_visit_time INTEGER,
                    hidden INTEGER DEFAULT 0
                )
            ''')
            
            # Insert only the current request history data
            for item in history_data:
                # Chrome history API returns timestamps in milliseconds since Unix epoch
                # We need to convert to Chrome's internal format (microseconds since 1601-01-01)
                chrome_time = item['lastVisitTime']
                
                # Convert from milliseconds since Unix epoch to microseconds since Chrome epoch (1601-01-01)
                # Chrome epoch starts at 1601-01-01 00:00:00 UTC
                # Unix epoch starts at 1970-01-01 00:00:00 UTC
                # Difference: 11644473600000 milliseconds
                # Convert to microseconds and add Chrome epoch offset
                unix_milliseconds = chrome_time
                
                # Validate timestamp bounds to prevent SQLite overflow
                if unix_milliseconds < 0 or unix_milliseconds > 9999999999999:  # Reasonable bounds
                    logger.warning(f"Invalid timestamp value: {unix_milliseconds}, using current time")
                    unix_milliseconds = int(datetime.now().timestamp() * 1000)
                
                chrome_microseconds = (unix_milliseconds * 1000) + (11644473600000 * 1000)
                
                cursor.execute('''
                    INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item['url'],
                    item['title'],
                    item['visitCount'],
                    0,  # typed_count
                    chrome_microseconds,
                    0   # hidden
                ))
            
            conn.commit()
            conn.close()
            
            # Extract and process history using the temporary database (only current request URLs)
            logger.info(f"Calling pipeline with temp_db_path={temp_db_path}, with_content=True, embed=True")
            result = extract_and_process_history(
                browser='chrome',  # Assume Chrome format
                db_path=temp_db_path,
                with_content=True,
                embed=True,
                embedder_backend='sentence-transformers',
                persist_directory=VECTOR_STORE_DIR,
                existing_urls=existing_urls  # Pass existing URLs to avoid reprocessing
            )
            logger.info(f"Pipeline returned status: {result.get('status')}, results count: {len(result.get('results', []))}")
            
            # Clean up temporary database
            try:
                os.remove(temp_db_path)
            except:
                pass
            
            # Return results based on pipeline status
            if result['status'] == 'embedded':
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=result['num_embedded'],
                    message=f"History data processed successfully. {result['num_embedded']} new items embedded and stored in vector database."
                )
            elif result['status'] == 'fetched':
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=len(result['results']),
                    message=f"History data processed successfully. {len(result['results'])} items fetched but not embedded."
                )
            elif result['status'] == 'no_valid_documents':
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=0,
                    message="History data processed but no valid documents found for embedding."
                )
            elif result['status'] == 'no_new_documents':
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=0,
                    message="No new history items found. All existing data is already processed."
                )
            else:
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=len(result['results']),
                    message=f"History data processed with status: {result['status']}"
                )
            
        except ImportError as e:
            # Fallback if dependencies are not available
            logger.warning(f"Pipeline dependencies not available: {e}")
            
            # Even in fallback mode, we can still create the SQLite database
            try:
                import sqlite3
                import os
                
                # Create a persistent SQLite database from the extension data
                db_dir = HISTORY_DB_DIR
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, 'extension_history.sqlite')
                
                # Create the SQLite database with Chrome-compatible schema
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Create the urls table (Chrome-compatible schema) if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS urls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT,
                        title TEXT,
                        visit_count INTEGER,
                        typed_count INTEGER,
                        last_visit_time INTEGER,
                        hidden INTEGER DEFAULT 0
                    )
                ''')
                
                # Insert the history data
                for item in history_data:
                    # Convert timestamp to Unix seconds for SQLite storage
                    chrome_time = item['lastVisitTime']
                    
                    # Validate timestamp bounds to prevent SQLite overflow
                    if chrome_time < 0 or chrome_time > 9999999999999:  # Reasonable bounds
                        logger.warning(f"Invalid timestamp value: {chrome_time}, using current time")
                        chrome_time = int(datetime.now().timestamp() * 1000)
                    
                    # Convert to Unix timestamp (seconds since epoch) for SQLite storage
                    unix_seconds = chrome_time // 1000
                    
                    cursor.execute('''
                        INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        item['url'],
                        item['title'],
                        item['visitCount'],
                        0,  # typed_count
                        unix_seconds,
                        0   # hidden
                    ))
                
                conn.commit()
                conn.close()
                
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=len(history_data),
                    message=f"History data stored in SQLite format. {len(history_data)} items processed (embedding not available)."
                )
                
            except Exception as db_error:
                logger.error(f"Failed to create SQLite database: {db_error}")
                return ProcessHistoryResponse(
                    success=True,
                    processed_count=len(history_data),
                    message="History data processed successfully (simplified - no embedding or database storage)"
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"History processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"History processing failed: {str(e)}"
        )

@app.get(
    "/api/stats",
    response_model=StatsResponse,
    summary="Get Statistics",
    description="Get vector store statistics",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        503: {"model": ErrorResponse, "description": "HistoryHounder backend unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["System"]
)
async def get_stats():
    """Get vector store statistics"""
    if not HISTORYHOUNDER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="HistoryHounder backend not available"
        )
    
    try:
        # Get vector store statistics
        store = ChromaVectorStore(persist_directory=VECTOR_STORE_DIR)
        
        try:
            # Get actual document count from ChromaDB
            document_count = store.count()
            
            # Get sample documents to show what's stored
            sample_docs = []
            if document_count > 0:
                try:
                    # Get a few sample documents
                    results = store.collection.query(
                        query_embeddings=[[0.0] * 768],  # Dummy embedding
                        n_results=min(5, document_count),
                        include=["metadatas", "documents"]
                    )
                    if results['metadatas'] and results['metadatas'][0]:
                        sample_docs = [
                            {
                                'url': meta.get('url', 'Unknown'),
                                'title': meta.get('title', 'Unknown'),
                                'timestamp': meta.get('last_visit_time', 'Unknown')
                            }
                            for meta in results['metadatas'][0]
                        ]
                except Exception as e:
                    logger.warning(f"Failed to get sample documents: {e}")
            
            stats = {
                'collections': 1,
                'documents': document_count,
                'status': 'available',
                'vector_store_path': VECTOR_STORE_DIR,
                'sample_documents': sample_docs
            }
        except Exception as e:
            logger.warning(f"Failed to get document count: {e}")
            # Provide basic stats if count fails
            stats = {
                'collections': 1,
                'documents': 0,
                'status': 'available',
                'vector_store_path': VECTOR_STORE_DIR,
                'sample_documents': []
            }
        finally:
            store.close()
        
        return StatsResponse(
            success=True,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Stats failed: {str(e)}"
        )

# Ollama model configuration
class ClearCacheResponse(BaseModel):
    """Clear cache response model"""
    success: bool = Field(..., description="Cache clear success status")
    message: str = Field(..., description="Clear cache status message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class OllamaModelResponse(BaseModel):
    """Ollama model configuration response"""
    current_model: str = Field(..., description="Currently configured model")
    available_models: List[str] = Field(default=[], description="List of available models")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

@app.post(
    "/api/clear-cache",
    response_model=ClearCacheResponse,
    summary="Clear Cache",
    description="Clear vector store and history database",
    responses={
        200: {"description": "Cache cleared successfully"},
        503: {"model": ErrorResponse, "description": "HistoryHounder backend unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    tags=["System"]
)
async def clear_cache():
    """Clear vector store and history database"""
    if not HISTORYHOUNDER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="HistoryHounder backend not available"
        )
    
    try:
        import shutil
        import os
        
        cleared_items = []
        
        # Clear vector store
        if os.path.exists(VECTOR_STORE_DIR):
            try:
                store = ChromaVectorStore(persist_directory=VECTOR_STORE_DIR)
                store.clear()
                store.close()
                cleared_items.append('vector store')
            except Exception as e:
                logger.warning(f"Failed to clear vector store: {e}")
        
        # Clear history database
        if os.path.exists('history_db'):
            try:
                shutil.rmtree('history_db')
                cleared_items.append('history database')
            except Exception as e:
                logger.warning(f"Failed to clear history database: {e}")
        
        if cleared_items:
            message = f"Successfully cleared: {', '.join(cleared_items)}"
        else:
            message = "No cache to clear"
        
        return ClearCacheResponse(
            success=True,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Clear cache failed: {str(e)}"
        )

@app.options("/api/clear-cache")
async def options_clear_cache():
    """Handle OPTIONS requests for clear-cache endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get(
    "/api/ollama/model",
    response_model=OllamaModelResponse,
    summary="Get Ollama Model",
    description="Get current Ollama model configuration",
    tags=["System"]
)
async def get_ollama_model():
    """Get current Ollama model configuration"""
    try:
        # For now, just return the configured model
        # In a full implementation, this could check available models via Ollama API
        return OllamaModelResponse(
            current_model=OLLAMA_MODEL,
            available_models=[OLLAMA_MODEL]  # Simplified for now
        )
    except Exception as e:
        logger.error(f"Ollama model info error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Ollama model info: {str(e)}"
        )

@app.options("/api/ollama/model")
async def options_ollama_model():
    """Handle OPTIONS requests for Ollama model endpoint"""
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("HistoryHounder API server starting...")
    logger.info(f"HistoryHounder backend available: {HISTORYHOUNDER_AVAILABLE}")
    logger.info(f"Ollama model: {OLLAMA_MODEL}")
    logger.info(f"Vector store directory: {VECTOR_STORE_DIR}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("HistoryHounder API server shutting down...")

def start_server(host: str = "localhost", port: int = 8080, reload: bool = False):
    """Start the HistoryHounder backend server"""
    print(f"🚀 Starting HistoryHounder Backend Server...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"🤖 Ollama Model: {OLLAMA_MODEL}")
    print(f"📖 API Documentation:")
    print(f"   Swagger UI: http://{host}:{port}/docs")
    print(f"   ReDoc: http://{host}:{port}/redoc")
    print(f"   OpenAPI JSON: http://{host}:{port}/openapi.json")
    print(f"🔗 Browser extension can connect to this server for enhanced features")
    print(f"Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "historyhounder.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='HistoryHounder Backend Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run server on')
    parser.add_argument('--host', type=str, default='localhost', help='Host to bind server to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    args = parser.parse_args()
    
    start_server(args.host, args.port, args.reload) 