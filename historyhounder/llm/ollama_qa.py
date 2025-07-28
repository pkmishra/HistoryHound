from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate


def answer_question_ollama(query, retriever, model="llama3.2:latest"):
    """
    Use LangChain RetrievalQA with Ollama as the LLM to answer a question given a retriever.
    Returns a dict with 'answer' and 'sources'.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting QA with query: {query}")
        logger.info(f"Using model: {model}")
        
        llm = OllamaLLM(model=model)
        
        # Test if Ollama is responding
        try:
            test_response = llm.invoke("Hello")
            logger.info(f"Ollama test response: {test_response[:100]}...")
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            return {
                "answer": "Sorry, I'm having trouble connecting to the AI model. Please check if Ollama is running and the model is available.",
                "sources": []
            }
        
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are an AI assistant analyzing browser history data. You have access to the following browsing history context:
{context}

CRITICAL RULES:
1. ONLY use information that is explicitly present in the provided context
2. DO NOT make assumptions or inferences beyond what the data shows
3. If the context is empty or insufficient, say "I don't have enough browsing history data to answer this question"
4. Always cite specific URLs, titles, visit times, and domains from the context when making claims
5. Be precise about what you can and cannot determine from the available data
6. For statistical questions, count and analyze the actual URLs, domains, and visit patterns shown in the data

When analyzing browsing patterns:
- Count the frequency of specific URLs and domains using the visit_count data
- Identify the most visited sites based on visit_count values provided
- Note visit times and patterns if available
- Distinguish between work-related and entertainment sites based on domains and titles
- Use visit_count to determine which sites are visited most frequently

For domain-specific questions (like "How many times did I visit github?"):
- Look for all URLs that contain the domain name in the URL or title
- Sum up the visit_count values for all matching URLs
- Provide the total count and list the specific URLs with their individual visit counts
- If no matching URLs are found, clearly state that no visits to that domain were found

When counting visits to a specific domain:
- Check both the URL and title fields for domain matches
- Add up all visit_count values for matching entries
- Provide a breakdown showing individual URLs and their visit counts
- Give the total sum as the final answer

Answer the user's question based STRICTLY on the provided browsing history context. If you cannot answer the question with the available data, acknowledge this limitation.

Question: {question}
Answer:
"""
        )
        
        logger.info("Creating RetrievalQA chain")
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt},
        )
        
        logger.info("Invoking QA chain")
        result = qa.invoke({"query": query})
        
        logger.info(f"QA result received, answer length: {len(result.get('result', ''))}")
        logger.info(f"Number of source documents: {len(result.get('source_documents', []))}")
        
        return {
            "answer": result["result"],
            "sources": [doc.page_content for doc in result["source_documents"]],
        }
        
    except Exception as e:
        logger.error(f"QA error: {e}")
        return {
            "answer": f"Sorry, I encountered an error while processing your question: {str(e)}",
            "sources": []
        } 