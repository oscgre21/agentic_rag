# PDF Document Processing for Knowledge Graph

This module adds PDF document processing capabilities to the knowledge graph RAG system.

## Features

- **PDF to Markdown Conversion**: Extracts text from PDF files and converts to markdown format
- **Batch Processing**: Processes all PDF files in a directory
- **Markdown Export**: Optionally saves converted markdown files for review
- **Integration**: Seamlessly integrates with existing Neo4j knowledge graph pipeline

## Usage

### 1. Basic Usage with PDF Documents

Create a directory for your PDF files:
```bash
mkdir pdfs
# Copy your PDF files to this directory
```

Run the PDF-specific script:
```bash
python kgraph_rag/bmi_graph_rag_pdf.py
```

### 2. Using PDF with the Original Script

Set environment variables to use PDF instead of Wikipedia:
```bash
export USE_PDF=true
export PDF_DIR=./pdfs
export MARKDOWN_DIR=./markdown_output  # Optional

python kgraph_rag/bmi_graph_rag.py
```

### 3. Environment Variables

Add these to your `.env` file:
```env
# Existing variables
NEO4J_URI=your_neo4j_uri
NEO4J_USERNAME=your_neo4j_username
NEO4J_PASSWORD=your_neo4j_password

# New PDF-related variables
USE_PDF=true                    # Set to true to use PDF files instead of Wikipedia
PDF_DIR=./pdfs                  # Directory containing PDF files
MARKDOWN_DIR=./markdown_output  # Optional: Directory to save converted markdown
```

## API Usage

### PDFToMarkdownLoader

Basic loader that converts PDFs to LangChain documents:

```python
from pdf_loader import PDFToMarkdownLoader

loader = PDFToMarkdownLoader(pdf_dir="./pdfs")
documents = loader.load()
```

### PDFMarkdownLoader

Extended loader that also saves markdown files:

```python
from pdf_loader import PDFMarkdownLoader

loader = PDFMarkdownLoader(
    pdf_dir="./pdfs",
    markdown_dir="./markdown_output",
    glob_pattern="*.pdf"
)
documents = loader.load()
```

## How It Works

1. **PDF Reading**: Uses `pypdf` to extract text from PDF files
2. **Markdown Conversion**: 
   - Identifies potential headers (all caps, short lines)
   - Preserves paragraph structure
   - Cleans up formatting
3. **Document Creation**: Creates LangChain documents with metadata:
   - `source`: Full path to PDF file
   - `page`: Page number in PDF
   - `filename`: Name of PDF file
   - `file_type`: Always "pdf"
4. **Graph Generation**: Documents are processed by LLMGraphTransformer to extract entities and relationships

## Troubleshooting

### No PDFs Found
- Ensure PDF files are in the correct directory
- Check file permissions
- Verify PDF_DIR environment variable

### Extraction Errors
- Some PDFs may have encoding issues
- Scanned PDFs without text layers won't work (OCR needed)
- Password-protected PDFs are not supported

### Memory Issues
- Large PDFs are processed in batches
- Adjust `batch_size` in the script if needed
- Consider splitting very large PDFs