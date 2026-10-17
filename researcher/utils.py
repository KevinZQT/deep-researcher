from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from datetime import  datetime
from typing import Any
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


def get_search_topic(messages: list[BaseMessage]) -> str:

    if len(messages) == 1:
        search_topic = messages[-1].content

    else:
        search_topic = ""
        for message in messages:
            if isinstance(message, HumanMessage):
                search_topic += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                search_topic += f"Assistant: {message.content}\n"
    return search_topic     

def get_url_map(chunks:list[Any], id:int) -> dict[str, str]:

    raw_urls = [chunk.web.uri for chunk in chunks
                if getattr(chunk, "web", None) and chunk.web.uri]

    prefix = f"prefix://id/"

    url_map = {}
    for idx, url in enumerate(raw_urls):
        if url not in url_map:
            url_map[url] = f"{prefix}{id}-{idx}"
    return url_map



def insert_citation_markers(text, citations_list):

    sorted_citations = sorted(
        citations_list, key=lambda c: (c["end_index"], c["start_index"]), reverse=True
    )

    modified_text = text
    for citation_info in sorted_citations:

        end_idx = citation_info["end_index"]
        marker_to_insert = ""
        for segment in citation_info["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"
        modified_text = (
            modified_text[:end_idx] + marker_to_insert + modified_text[end_idx:]
        )

    return modified_text

def get_citations(response, url_map:dict[str, str]) -> list:

    citations = []

    if not response or not response.candidates:
        return citations

    candidate = response.candidates[0]
    if (
        not hasattr(candidate, "grounding_metadata")
        or not candidate.grounding_metadata
        or not hasattr(candidate.grounding_metadata, "grounding_supports")
    ):
        return citations

    for support in candidate.grounding_metadata.grounding_supports or []:
        citation = {}

        if not hasattr(support, "segment") or support.segment is None:
            continue  

        start_index = (
            support.segment.start_index
            if support.segment.start_index is not None
            else 0
        )

        if support.segment.end_index is None:
            continue  


        citation["start_index"] = start_index
        citation["end_index"] = support.segment.end_index

        citation["segments"] = []
        if (
            hasattr(support, "grounding_chunk_indices")
            and support.grounding_chunk_indices
        ):
            for ind in support.grounding_chunk_indices:
                try:
                    chunks = candidate.grounding_metadata.grounding_chunks or []
                    if not isinstance(ind, int) or ind < 0:
                        continue
                    chunk = chunks[ind]
                    resolved_url = url_map.get(chunk.web.uri, None)
                    if not resolved_url:
                        continue
                    citation["segments"].append(
                        {
                            "label": (chunk.web.title or chunk.web.uri).replace("[", "(").replace("]", ")"),
                            "short_url": resolved_url,
                            "value": chunk.web.uri,
                        }
                    )
                except (IndexError, AttributeError, TypeError):

                    pass
        citations.append(citation)
    return citations



