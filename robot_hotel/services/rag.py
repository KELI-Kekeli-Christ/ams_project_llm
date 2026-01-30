import os
import torch
from pathlib import Path
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    StorageContext, 
    load_index_from_storage,
    Settings
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Configuration des chemins
BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "docs"
STORAGE_DIR = BASE_DIR / "storage"  # Dossier pour sauvegarder l'index

_rag_index = None
_retriever = None

def init_rag():
    global _rag_index, _retriever
    
    if _rag_index is not None:
        return _rag_index

    # 1. Configuration globale (évite de passer le modèle partout)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device=device
    )
    Settings.chunk_size = 512  # Chunks plus petits = recherche plus rapide et précise

    # 2. Stratégie de chargement (Persistance)
    if STORAGE_DIR.exists() and any(STORAGE_DIR.iterdir()):
        print("💾 Chargement de l'index depuis le stockage local...")
        storage_context = StorageContext.from_defaults(persist_dir=str(STORAGE_DIR))
        _rag_index = load_index_from_storage(storage_context)
    else:
        print("⚡ Premier lancement : Indexation des documents...")
        if not DOCS_DIR.exists():
            print(f"❌ Erreur : {DOCS_DIR} introuvable.")
            return None
        
        documents = SimpleDirectoryReader(str(DOCS_DIR)).load_data()
        _rag_index = VectorStoreIndex.from_documents(documents)
        
        # Sauvegarde pour le prochain démarrage
        STORAGE_DIR.mkdir(exist_ok=True)
        _rag_index.storage_context.persist(persist_dir=str(STORAGE_DIR))
        print(f"✅ Index créé et sauvegardé dans {STORAGE_DIR}")

    # 3. Pré-calcul du retriever (Gain de temps à l'exécution)
    _retriever = _rag_index.as_retriever(similarity_top_k=2) # 2 c'est souvent assez pour Pepper
    
    return _rag_index

def get_rag_context(user_msg: str,top_k: int = 3) -> dict:
    """Recherche ultra-rapide avec retriever pré-chargé."""
    if _retriever is None:
        init_rag()

    try:
        # Recherche directe sur le retriever pré-initialisé
        nodes = _retriever.retrieve(user_msg)
        
        if not nodes:
            return {"text": "", "used": False}

        # Construction concise du contexte
        context = "\n\n".join([n.text.strip() for n in nodes])
        
        return {
            "text": context[:2500], # On limite pour ne pas ralentir le LLM
            "used": True
        }
    
    except Exception as e:
        print(f"⚠️ Erreur RAG : {e}")
        return {"text": "", "used": False}