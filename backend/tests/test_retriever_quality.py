from unittest.mock import patch

from retrieval.retriever import AdvancedRetriever, KB_PATHS


def _retriever_with_documents(documents):
    retriever = AdvancedRetriever.__new__(AdvancedRetriever)
    retriever.top_n = 5
    retriever.knowledge_map = {key: content for key, content in documents.items()}
    retriever.source_map = {key: "test" for key in documents}
    retriever.file_map = {key: f"{key}.md" for key in documents}
    return retriever


def test_top_n_documents_are_used_in_synthesis():
    retriever = _retriever_with_documents(
        {
            "first": "Brahman is described in the first source with a distinct explanation.",
            "second": "Brahman is described in the second source with another distinct detail.",
            "third": "Brahman is described in the third source with a final distinct detail.",
        }
    )
    results = retriever.retrieve_multi("What is Brahman?")

    response = retriever.reason_and_compare(results, "What is Brahman?")

    assert response["metadata"]["docs_combined"] == 3
    assert "third source" in response["content"]


def test_duplicate_paragraphs_are_removed():
    paragraph = "Brahman is the ultimate reality described in this source."
    results = [
        {"content": f"{paragraph}\n\nFirst distinct evidence paragraph.", "file": "one.md"},
        {"content": f"{paragraph}\n\nSecond distinct evidence paragraph.", "file": "two.md"},
    ]

    combined = AdvancedRetriever._combine_evidence(results)

    assert combined.count(paragraph) == 1
    assert "First distinct evidence paragraph." in combined
    assert "Second distinct evidence paragraph." in combined


def test_generic_prompt_words_do_not_match_unrelated_documents():
    retriever = _retriever_with_documents(
        {
            "quantum_notes": "This page discusses one model and any related system name.",
            "upanishads": "The Taittiriya Upanishad teaches about Brahman and the self.",
        }
    )

    results = retriever.retrieve_multi("Name any one Upanishad.")

    assert results
    assert results[0]["file"] == "upanishads.md"
    assert all(row["file"] != "quantum_notes.md" for row in results)


def test_sanskrit_knowledge_tree_is_loaded():
    retriever = AdvancedRetriever()

    assert "sanskrit" in KB_PATHS
    assert "brahman" in retriever.knowledge_map
    assert retriever.file_map["brahman"] == "brahman.md"


def test_synthesis_failure_falls_back_to_primary_document():
    retriever = _retriever_with_documents(
        {"brahman": "Brahman is supported by this complete source document."}
    )
    results = retriever.retrieve_multi("What is Brahman?")
    primary_content = results[0]["content"]

    with patch.object(AdvancedRetriever, "_synthesize_evidence", side_effect=RuntimeError("forced failure")):
        response = retriever.reason_and_compare(results, "What is Brahman?")

    assert response["content"] == primary_content
