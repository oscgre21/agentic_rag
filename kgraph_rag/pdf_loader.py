import os
from typing import List, Dict, Optional
from pathlib import Path
import pypdf
from langchain.schema import Document
from langchain.document_loaders.base import BaseLoader
import re


class PDFToMarkdownLoader(BaseLoader):
    """Loader that reads PDF files and converts them to markdown format."""
    
    def __init__(self, pdf_dir: str, glob_pattern: str = "*.pdf"):
        """
        Initialize the PDF loader.
        
        Args:
            pdf_dir: Directory containing PDF files
            glob_pattern: Pattern to match PDF files (default: "*.pdf")
        """
        self.pdf_dir = Path(pdf_dir)
        self.glob_pattern = glob_pattern
        
    def _extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, str]]:
        """Extract text from PDF file page by page."""
        pages_data = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        pages_data.append({
                            "text": text,
                            "page": page_num + 1,
                            "source": str(pdf_path)
                        })
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {str(e)}")
            
        return pages_data
    
    def _convert_to_markdown(self, text: str) -> str:
        """Convert extracted text to markdown format."""
        # Clean up text
        text = text.strip()
        
        # Try to identify headers (lines that are all caps or followed by empty lines)
        lines = text.split('\n')
        markdown_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                markdown_lines.append("")
                continue
                
            # Check if line might be a header
            if len(line) < 100:  # Headers are usually shorter
                # All caps likely a header
                if line.isupper() and len(line.split()) > 1:
                    markdown_lines.append(f"## {line.title()}")
                # Line followed by empty line might be header
                elif i + 1 < len(lines) and not lines[i + 1].strip():
                    markdown_lines.append(f"### {line}")
                else:
                    markdown_lines.append(line)
            else:
                # Regular paragraph
                markdown_lines.append(line)
        
        # Join lines and clean up multiple empty lines
        markdown_text = '\n'.join(markdown_lines)
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        return markdown_text
    
    def load(self) -> List[Document]:
        """Load all PDF files from the directory and convert to documents."""
        documents = []
        
        # Check if directory exists
        if not self.pdf_dir.exists():
            raise ValueError(f"Directory {self.pdf_dir} does not exist")
        
        # Find all PDF files
        pdf_files = list(self.pdf_dir.glob(self.glob_pattern))
        
        if not pdf_files:
            print(f"No PDF files found in {self.pdf_dir} matching pattern {self.glob_pattern}")
            return documents
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF
        for pdf_path in pdf_files:
            print(f"Processing {pdf_path.name}...")
            pages_data = self._extract_text_from_pdf(pdf_path)
            
            # Convert each page to a document
            for page_data in pages_data:
                markdown_content = self._convert_to_markdown(page_data["text"])
                
                if markdown_content.strip():
                    doc = Document(
                        page_content=markdown_content,
                        metadata={
                            "source": page_data["source"],
                            "page": page_data["page"],
                            "filename": pdf_path.name,
                            "file_type": "pdf"
                        }
                    )
                    documents.append(doc)
        
        print(f"Successfully loaded {len(documents)} documents from PDF files")
        return documents


class PDFMarkdownLoader(BaseLoader):
    """Alternative loader that saves markdown files after conversion."""
    
    def __init__(self, pdf_dir: str, markdown_dir: Optional[str] = None, glob_pattern: str = "*.pdf"):
        """
        Initialize the PDF loader with markdown output.
        
        Args:
            pdf_dir: Directory containing PDF files
            markdown_dir: Directory to save markdown files (optional)
            glob_pattern: Pattern to match PDF files (default: "*.pdf")
        """
        self.base_loader = PDFToMarkdownLoader(pdf_dir, glob_pattern)
        self.markdown_dir = Path(markdown_dir) if markdown_dir else None
        
        if self.markdown_dir:
            self.markdown_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> List[Document]:
        """Load PDF files and optionally save as markdown."""
        documents = self.base_loader.load()
        
        if self.markdown_dir:
            # Group documents by source file
            docs_by_source = {}
            for doc in documents:
                source = doc.metadata["filename"]
                if source not in docs_by_source:
                    docs_by_source[source] = []
                docs_by_source[source].append(doc)
            
            # Save each file as markdown
            for filename, file_docs in docs_by_source.items():
                md_filename = filename.replace('.pdf', '.md')
                md_path = self.markdown_dir / md_filename
                
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {filename}\n\n")
                    
                    for doc in sorted(file_docs, key=lambda x: x.metadata["page"]):
                        f.write(f"## Page {doc.metadata['page']}\n\n")
                        f.write(doc.page_content)
                        f.write("\n\n---\n\n")
                
                print(f"Saved markdown to {md_path}")
        
        return documents