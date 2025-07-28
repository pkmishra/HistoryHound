import chromadb
from chromadb.config import Settings
from typing import List, Dict
from datetime import datetime
import gc

def convert_metadata_for_chroma(metadata_dict):
    """Convert metadata values to ChromaDB-compatible types."""
    converted = {}
    for k, v in metadata_dict.items():
        if v is None:
            # ChromaDB doesn't accept None values, convert to empty string
            converted[k] = ""
        elif isinstance(v, datetime):
            converted[k] = v.isoformat()
        elif isinstance(v, (str, int, float, bool)):
            converted[k] = v
        else:
            # Convert any other types to string
            converted[k] = str(v)
    return converted

class ChromaVectorStore:
    """
    Vector store using ChromaDB. Stores embeddings and metadata.
    """
    def __init__(self, persist_directory="chroma_db"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection("history")

    def add(self, docs: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
        # Convert metadata to ChromaDB-compatible types
        converted_metadatas = [convert_metadata_for_chroma(metadata) for metadata in metadatas]
        
        # Use URL as ID to prevent duplicates and enable updates
        ids = [meta.get('url', str(i)) for i, meta in enumerate(converted_metadatas)]
        
        # Delete existing entries with the same URLs to avoid duplicates
        if ids:
            try:
                # Get existing IDs to avoid deleting non-existent ones
                existing_results = self.collection.get(ids=ids, include=[])
                if existing_results and existing_results['ids']:
                    existing_ids = existing_results['ids']
                    self.collection.delete(ids=existing_ids)
            except Exception:
                # If deletion fails, continue
                pass
        
        # Add new documents
        self.collection.add(
            documents=docs,
            embeddings=embeddings,
            metadatas=converted_metadatas,
            ids=ids
        )

    def query(self, query_embedding: List[float], top_k=5):
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"]
        )
        return results 

    def count(self):
        # Returns the number of documents in the collection
        return self.collection.count() 
    
    def clear(self):
        """Clear all documents from the collection"""
        try:
            # Get all IDs and delete them
            results = self.collection.get(include=[])
            if results and results['ids']:
                print(f"Clearing {len(results['ids'])} documents from vector store")
                self.collection.delete(ids=results['ids'])
            else:
                print("No documents to clear from vector store")
        except Exception as e:
            # If collection is empty or other error, ignore
            print(f"Error clearing vector store: {e}")
            pass
    
    def delete_by_urls(self, urls: List[str]):
        """Delete documents by their URLs"""
        try:
            self.collection.delete(ids=urls)
        except Exception as e:
            # If URLs don't exist, ignore
            pass

    def close(self):
        # Attempt to close the client and force a flush to disk
        try:
            if hasattr(self.client, 'close'):
                self.client.close()
        except Exception:
            pass
        del self.client
        del self.collection
        gc.collect() 