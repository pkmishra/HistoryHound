import pytest
from historyhounder.llm import ollama_qa

class DummyRetriever:
    def __init__(self):
        self.called = False
    def get_relevant_documents(self, query):
        self.called = True
        return [DummyDoc('context1'), DummyDoc('context2')]

class DummyDoc:
    def __init__(self, content):
        self.page_content = content

class DummyQA:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def __call__(self, inputs):
        return {"result": "The answer is 42.", "source_documents": [DummyDoc('context1'), DummyDoc('context2')]}
    def invoke(self, inputs):
        return self.__call__(inputs)

class DummyPrompt:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

def test_answer_question_ollama(monkeypatch):
    monkeypatch.setattr(ollama_qa, 'OllamaLLM', lambda model: 'llm')
    monkeypatch.setattr(ollama_qa, 'PromptTemplate', DummyPrompt)
    monkeypatch.setattr(ollama_qa, 'RetrievalQA', type('Q', (), {'from_chain_type': staticmethod(lambda **kwargs: DummyQA(**kwargs))}))
    retriever = DummyRetriever()
    result = ollama_qa.answer_question_ollama('What is the answer?', retriever, model='llama3.2:latest')
    assert result['answer'] == 'The answer is 42.'
    assert result['sources'] == ['context1', 'context2']


def test_answer_question_ollama_empty_context(monkeypatch):
    monkeypatch.setattr(ollama_qa, 'OllamaLLM', lambda model: 'llm')
    monkeypatch.setattr(ollama_qa, 'PromptTemplate', DummyPrompt)
    monkeypatch.setattr(ollama_qa, 'RetrievalQA', type('Q', (), {'from_chain_type': staticmethod(lambda **kwargs: DummyQA(**kwargs))}))
    class EmptyRetriever:
        def get_relevant_documents(self, query):
            return []
    retriever = EmptyRetriever()
    result = ollama_qa.answer_question_ollama('What is the answer?', retriever, model='llama3.2:latest')
    assert result['answer'] == 'The answer is 42.' or result['answer'] == ''
    # Should handle empty sources gracefully
    assert isinstance(result['sources'], list)


def test_answer_question_ollama_error(monkeypatch):
    class ErrorQA:
        def __init__(self, **kwargs):
            pass
        def __call__(self, inputs):
            raise Exception('QA error')
        def invoke(self, inputs):
            raise Exception('QA error')
    monkeypatch.setattr(ollama_qa, 'OllamaLLM', lambda model: 'llm')
    monkeypatch.setattr(ollama_qa, 'PromptTemplate', DummyPrompt)
    monkeypatch.setattr(ollama_qa, 'RetrievalQA', type('Q', (), {'from_chain_type': staticmethod(lambda **kwargs: ErrorQA(**kwargs))}))
    retriever = DummyRetriever()
    with pytest.raises(Exception) as excinfo:
        ollama_qa.answer_question_ollama('What is the answer?', retriever, model='llama3.2:latest')
    assert 'QA error' in str(excinfo.value) 