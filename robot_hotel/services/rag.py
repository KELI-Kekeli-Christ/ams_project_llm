# services/rag.py
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"
_rag_index = None

def init_rag():
    global _rag_index
    print("\n" + "="*60)
    print("INITIALISATION RAG")
    print("="*60)
    
    if _rag_index is not None:
        print("RAG déjà initialisé.")
        return _rag_index

    if not DOCS_DIR.exists():
        print(f"ERREUR : Dossier 'docs' introuvable : {DOCS_DIR}")
        return None

    print(f"Chargement des documents depuis : {DOCS_DIR}")
    documents = SimpleDirectoryReader(str(DOCS_DIR)).load_data()
    
    if not documents:
        print("ERREUR : Aucun document trouvé dans 'docs/'")
        return None

    print(f"{len(documents)} documents chargés :")
    for doc in documents[:3]:
        fname = doc.metadata.get('file_name', 'inconnu')
        preview = doc.text[:100].replace('\n', ' ')
        print(f"   • {fname} → {preview}...")

    print("Chargement du modèle d'embedding...")
    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu"
    )
    print("Embedding OK")

    print("Indexation en cours...")
    _rag_index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    print("INDEX RAG PRÊT !\n")
    return _rag_index

def get_rag_context(user_msg: str, top_k: int = 3) -> dict:
    print(f"\nRECHERCHE RAG pour : '{user_msg}'")
    if _rag_index is None:
        print("Index non initialisé → pas de contexte")
        return {"text": "", "used": False, "debug": "RAG non initialisé"}

    try:
        retriever = _rag_index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(user_msg)
        
        if not nodes:
            print("Aucun résultat trouvé (similarité trop faible)")
            return {"text": "", "used": False, "debug": "Aucun résultat"}

        print(f"{len(nodes)} résultats trouvés :")
        context_parts = []
        for i, node in enumerate(nodes):
            text = node.text.strip()
            score = node.score
            file = node.metadata.get('file_name', 'inconnu')
            print(f"   [{i+1}] Score: {score:.3f} | {file}")
            print(f"       → {text[:150]}...")
            context_parts.append(text)
        
        context = "\n\n".join(context_parts)[:3000]
        print(f"Contexte final envoyé ({len(context)} caractères)")
        return {
            "text": context,
            "used": True,
            "debug": f"{len(nodes)} résultats, top_k={top_k}"
        }
    
    except Exception as e:
        print(f"ERREUR RAG : {e}")
        return {"text": "", "used": False, "debug": str(e)}