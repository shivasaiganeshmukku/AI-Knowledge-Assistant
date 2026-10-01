from gemini import generate_embedding, generate_response
from vector_store import search_documents


DISTANCE_THRESHOLD = 0.8


def answer_question(question):
    query_embedding = generate_embedding(question)

    relevant_chunks, metadatas, distances = search_documents(query_embedding)

    filtered_results = [
        (chunk, metadata, distance)
        for chunk, metadata, distance in zip(
            relevant_chunks,
            metadatas,
            distances
        )
        if distance <= DISTANCE_THRESHOLD
    ]

    if not filtered_results:
        return {
            "answer": "I couldn't find relevant information in the uploaded documents.",
            "sources": []
        }

    context = "\n\n".join(
        chunk
        for chunk, metadata, distance in filtered_results
    )

    prompt = f"""
Use the following context to answer the question.

Context:
{context}

Question:
{question}
"""

    answer = generate_response(prompt)

    return {
        "answer": answer,
        "sources": [
            {
                "filename": metadata["filename"],
                "chunk_id": metadata["chunk_id"],
                "text": chunk
            }
            for chunk, metadata, distance in filtered_results
        ]
    }


def debug_retrieval(question):
    query_embedding = generate_embedding(question)

    relevant_chunks, metadatas, distances = search_documents(
        query_embedding
    )

    filtered_results = [
        (chunk, metadata, distance)
        for chunk, metadata, distance in zip(
            relevant_chunks,
            metadatas,
            distances
        )
        if distance <= DISTANCE_THRESHOLD
    ]

    return {
        "question": question,
        "total_retrieved": len(relevant_chunks),
        "results": [
            {
                "filename": metadata["filename"],
                "chunk_id": metadata["chunk_id"],
                "distance": distance,
                "relevant": distance <= DISTANCE_THRESHOLD,
                "text": chunk
            }
            for chunk, metadata, distance in zip(
                relevant_chunks,
                metadatas,
                distances
            )
        ],
        "filtered_count": len(filtered_results)
    }

def debug_rag_prompt(question):
    query_embedding = generate_embedding(question)

    relevant_chunks, metadatas, distances = search_documents(
        query_embedding
    )

    filtered_results = [
        (chunk, metadata, distance)
        for chunk, metadata, distance in zip(
            relevant_chunks,
            metadatas,
            distances
        )
        if distance <= DISTANCE_THRESHOLD
    ]

    if not filtered_results:
        return {
            "question": question,
            "context": "",
            "prompt": None,
            "sources": []
        }

    context = "\n\n".join(
        chunk
        for chunk, metadata, distance in filtered_results
    )

    prompt = f"""
You are a knowledge assistant.

Answer the user's question using only the information provided in the context below.

If the answer cannot be found in the context, say:
"I couldn't find the answer in the uploaded documents."

Do not invent or add information that is not supported by the context.

Context:
{context}

Question:
{question}
"""

    return {
        "question": question,
        "context": context,
        "prompt": prompt,
        "sources": [
            {
                "filename": metadata["filename"],
                "chunk_id": metadata["chunk_id"],
                "distance": distance
            }
            for chunk, metadata, distance in filtered_results
        ]
    }