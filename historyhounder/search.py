from langchain_chroma import Chroma as LCChroma
from langchain_huggingface import HuggingFaceEmbeddings
from historyhounder.embedder import get_embedder
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.llm.ollama_qa import answer_question_ollama

def semantic_search(query, top_k=5, embedder_backend='sentence-transformers', persist_directory='chroma_db'):
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    query_emb = embedder.embed([query])[0]
    results = store.query(query_emb, top_k=top_k)
    output = []
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        dist = results['distances'][0][i]
        output.append({**meta, 'document': doc, 'distance': dist})
    return output

def llm_qa_search(query, top_k=5, llm='ollama', llm_model='llama3'):
    lc_chroma = LCChroma(
        persist_directory="chroma_db",
        embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )
    retriever = lc_chroma.as_retriever(search_kwargs={"k": top_k})
    result = answer_question_ollama(query, retriever, model=llm_model)
    return {
        'answer': result['answer'],
        'sources': result['sources']
    } 