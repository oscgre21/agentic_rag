#!/usr/bin/env python3
"""Test script for PDF loader functionality."""

import os
from pathlib import Path
from pdf_loader import PDFToMarkdownLoader, PDFMarkdownLoader

def test_pdf_loader():
    """Test the PDF loader with sample content."""
    
    # Check if PDF directory exists
    pdf_dir = "./pdfs"
    if not Path(pdf_dir).exists():
        print(f"Creating {pdf_dir} directory...")
        Path(pdf_dir).mkdir(exist_ok=True)
    
    # Check if there are any PDFs
    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
    if not pdf_files:
        print(f"\nNo PDF files found in {pdf_dir}")
        print("Please add some PDF files to test the loader.")
        print("\nYou can download sample PDFs from:")
        print("- https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf")
        print("- https://arxiv.org/pdf/2301.00303.pdf (LangChain paper)")
        return
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    
    # Test basic loader
    print("\n" + "="*50)
    print("Testing PDFToMarkdownLoader...")
    print("="*50)
    
    loader = PDFToMarkdownLoader(pdf_dir=pdf_dir)
    documents = loader.load()
    
    print(f"\nLoaded {len(documents)} documents")
    if documents:
        print(f"\nFirst document preview:")
        print(f"Source: {documents[0].metadata['source']}")
        print(f"Page: {documents[0].metadata['page']}")
        print(f"Content (first 500 chars):\n{documents[0].page_content[:500]}...")
    
    # Test loader with markdown output
    print("\n" + "="*50)
    print("Testing PDFMarkdownLoader with markdown output...")
    print("="*50)
    
    markdown_loader = PDFMarkdownLoader(
        pdf_dir=pdf_dir,
        markdown_dir="./markdown_output"
    )
    documents = markdown_loader.load()
    
    print(f"\nCheck ./markdown_output for converted markdown files")
    
    # Show statistics
    print("\n" + "="*50)
    print("Document Statistics:")
    print("="*50)
    
    total_chars = sum(len(doc.page_content) for doc in documents)
    avg_chars = total_chars // len(documents) if documents else 0
    
    print(f"Total documents: {len(documents)}")
    print(f"Total characters: {total_chars:,}")
    print(f"Average characters per document: {avg_chars:,}")
    
    # Group by source file
    docs_by_file = {}
    for doc in documents:
        filename = doc.metadata['filename']
        if filename not in docs_by_file:
            docs_by_file[filename] = 0
        docs_by_file[filename] += 1
    
    print("\nDocuments per file:")
    for filename, count in docs_by_file.items():
        print(f"  - {filename}: {count} documents")

if __name__ == "__main__":
    test_pdf_loader()