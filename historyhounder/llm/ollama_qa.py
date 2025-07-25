from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate


def answer_question_ollama(query, retriever, model="llama3.2:latest"):
    """
    Use LangChain RetrievalQA with Ollama as the LLM to answer a question given a retriever.
    Returns a dict with 'answer' and 'sources'.
    """
    llm = OllamaLLM(model=model)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are an assistant with access to the following browser history context:
{context}

Answer the user's question as accurately as possible using only the provided context. If the answer is not in the context, say you don't know.

Question: {question}
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