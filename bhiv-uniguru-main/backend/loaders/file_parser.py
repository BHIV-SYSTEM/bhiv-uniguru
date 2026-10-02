import os
import fitz  # PyMuPDF
from typing import Dict, Any, Optional

class FileParser:
    """
    Parses various file formats and extracts text and metadata.
    Supported: .md, .txt, .pdf
    """
    
    @staticmethod
    def parse(file_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return None
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".md":
            return FileParser.parse_markdown(file_path)
        elif ext == ".txt":
            return FileParser.parse_text(file_path)
        elif ext == ".pdf":
            return FileParser.parse_pdf(file_path)
        return None

    @staticmethod
    def parse_markdown(file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            metadata = {
                "source": os.path.basename(file_path),
                "path": file_path,
                "author": "Unknown",
                "publication": "Unknown",
                "type": "markdown"
            }
            
            # Extract metadata from YAML-like frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    header = parts[1]
                    body = parts[2].strip()
                    for line in header.strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            key = k.strip().lower()
                            if key in [
                                "author",
                                "publication",
                                "title",
                                "source",
                                "verification_status",
                                "category",
                                "url",
                            ]:
                                metadata[key] = v.strip()
                    return {"content": body, "metadata": metadata}
            
            return {"content": content, "metadata": metadata}
        except Exception as e:
            return {"content": "", "metadata": {"error": str(e), "path": file_path}}

    @staticmethod
    def parse_text(file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return {
                "content": content,
                "metadata": {
                    "source": os.path.basename(file_path),
                    "path": file_path,
                    "author": "Unknown",
                    "publication": "Unknown",
                    "type": "text"
                }
            }
        except Exception as e:
            return {"content": "", "metadata": {"error": str(e), "path": file_path}}

    @staticmethod
    def parse_pdf(file_path: str) -> Dict[str, Any]:
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            
            pdf_meta = doc.metadata
            metadata = {
                "source": os.path.basename(file_path),
                "path": file_path,
                "author": pdf_meta.get("author") or "Unknown",
                "publication": pdf_meta.get("producer") or "Unknown",
                "title": pdf_meta.get("title") or os.path.basename(file_path),
                "type": "pdf"
            }
            doc.close()
            return {"content": text, "metadata": metadata}
        except Exception as e:
            return {"content": "", "metadata": {"error": str(e), "path": file_path}}
