import chromadb


client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="knowledge_documents"
)



def document_hash_exists(file_hash):
    results = collection.get(
        where={"file_hash": file_hash},
        limit=1
    )

    return len(results["ids"]) > 0

def get_documents():
    results = collection.get(
        include=["metadatas"]
    )

    documents = {}

    for metadata in results["metadatas"]:
        filename = metadata["filename"]

        if filename not in documents:
            documents[filename] = 0

        documents[filename] += 1

    return [
        {
            "filename": filename,
            "chunks": chunk_count
        }
        for filename, chunk_count in documents.items()
    ]

def delete_document(filename):
    results = collection.get(
        where={"filename": filename}
    )

    ids = results["ids"]

    if not ids:
        return False

    collection.delete(ids=ids)

    return True

def add_documents(chunks, filename, file_hash):
    for index, chunk in enumerate(chunks):
        collection.add(
            ids=[f"{filename}_{index}"],
            documents=[chunk["text"]],
            embeddings=[chunk["embedding"]],
            metadatas=[{
                "filename": filename,
                "file_hash": file_hash, 
                "chunk_id": index
            }]
        )

def search_documents(query_embedding, n_results=3):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return documents, metadatas, distances