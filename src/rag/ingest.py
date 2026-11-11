"""
Ingestion, parsing, and chunking module for AgriMind Agricultural Knowledge Base.
"""
import os
import re
import json
from typing import List, Dict, Any

RAW_DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge_base", "raw")
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge_base", "metadata_manifest.json")
PROCESSED_CHUNKS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge_base", "processed_chunks.json")

def parse_markdown_with_frontmatter(file_path: str) -> Dict[str, Any]:
    """
    Parses Markdown file containing YAML-style frontmatter between --- markers.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError(f"Document {file_path} missing valid frontmatter enclosed in '---'.")

    raw_yaml = frontmatter_match.group(1)
    body = frontmatter_match.group(2).strip()

    # Simple robust YAML parser for key-value and list properties
    metadata = {}
    current_list_key = None

    for line in raw_yaml.splitlines():
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#"):
            continue

        if line_strip.startswith("- ") and current_list_key:
            metadata[current_list_key].append(line_strip[2:].strip())
        elif ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if val == "":
                current_list_key = key
                metadata[key] = []
            else:
                current_list_key = None
                # Strip quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                # Cast year to int if applicable
                if key == "publication_year":
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                metadata[key] = val

    metadata["body"] = body
    metadata["source_file"] = os.path.basename(file_path)
    return metadata

def recursive_chunk_text(text: str, chunk_size: int = 600, chunk_overlap: int = 100) -> List[str]:
    """
    Splits text recursively by paragraphs, sentences, and words to preserve semantic coherence.
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "; ", ", ", " "]
        )
        return splitter.split_text(text)
    except ImportError:
        # High-fidelity fallback implementation
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) > chunk_size:
                    # Split long paragraphs by sentences
                    sentences = re.split(r"(?<=[.?!])\s+", para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                            sub_chunk = f"{sub_chunk} {sent}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = sent
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = para
        if current_chunk:
            chunks.append(current_chunk)

        # Apply overlap
        overlapped_chunks = []
        for i, ch in enumerate(chunks):
            if i > 0 and chunk_overlap > 0:
                prev_text = chunks[i - 1]
                overlap_text = prev_text[-chunk_overlap:]
                # Align to nearest word boundary
                if " " in overlap_text:
                    overlap_text = overlap_text[overlap_text.find(" ") + 1:]
                overlapped_chunks.append(f"{overlap_text} ... {ch}")
            else:
                overlapped_chunks.append(ch)
        return overlapped_chunks

def process_knowledge_base(
    raw_dir: str = RAW_DOCS_DIR,
    manifest_path: str = MANIFEST_PATH,
    output_path: str = PROCESSED_CHUNKS_PATH,
    chunk_size: int = 600,
    chunk_overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Ingests all raw documents, chunks them, associates ChromaDB-compatible metadata,
    and saves processed chunks to JSON.
    """
    if not os.path.exists(raw_dir):
        raise FileNotFoundError(f"Raw documents directory not found: {raw_dir}")

    doc_files = sorted([f for f in os.listdir(raw_dir) if f.endswith(".md")])
    if not doc_files:
        raise ValueError(f"No markdown documents found in {raw_dir}")

    all_chunks = []
    
    for filename in doc_files:
        filepath = os.path.join(raw_dir, filename)
        doc = parse_markdown_with_frontmatter(filepath)
        
        body = doc.pop("body")
        doc_id = doc["doc_id"]
        
        raw_chunks = recursive_chunk_text(body, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # Flatten list fields for ChromaDB metadata compatibility (Chroma requires str, int, float, bool)
        disease_targets_str = ",".join(doc.get("disease_targets", [])) if isinstance(doc.get("disease_targets"), list) else str(doc.get("disease_targets", ""))
        categories_str = ",".join(doc.get("categories", [])) if isinstance(doc.get("categories"), list) else str(doc.get("categories", ""))
        authors_str = ", ".join(doc.get("authors", [])) if isinstance(doc.get("authors"), list) else str(doc.get("authors", ""))
        
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{doc_id}-C{idx+1:03d}"
            chunk_metadata = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "title": doc.get("title", ""),
                "institution": doc.get("institution", ""),
                "authors": authors_str,
                "publication_year": int(doc.get("publication_year", 2021)),
                "source_url": doc.get("source_url", ""),
                "disease_targets": disease_targets_str,
                "pathogen": doc.get("pathogen", ""),
                "pathogen_type": doc.get("pathogen_type", ""),
                "categories": categories_str,
                "chunk_index": idx + 1,
                "total_doc_chunks": len(raw_chunks),
            }
            
            all_chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "metadata": chunk_metadata
            })

    # Save processed chunks
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"Processed {len(doc_files)} documents into {len(all_chunks)} chunks.")
    print(f"Saved processed chunks to: {output_path}")
    return all_chunks

if __name__ == "__main__":
    chunks = process_knowledge_base()
