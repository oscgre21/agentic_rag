#!/usr/bin/env python3
"""
Script to update PDF metadata - sets the Title field to the filename (without extension)
for all PDF files in the ./docs directory.
"""

import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import argparse


def update_pdf_title(pdf_path):
    """
    Update the Title metadata of a PDF file to match its filename (without extension).
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the filename with extension
        filename_without_ext = pdf_path.name
        
        # Read the PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        
        # Copy all pages to writer
        for page in reader.pages:
            writer.add_page(page)
        
        # Get existing metadata or create new dict
        metadata = reader.metadata if reader.metadata else {}
        
        # Update the Title field
        metadata_update = {
            '/Title': filename_without_ext
        }
        
        # Preserve other metadata fields if they exist
        if metadata:
            for key, value in metadata.items():
                if key != '/Title':
                    metadata_update[key] = value
        
        # Add metadata to writer
        writer.add_metadata(metadata_update)
        
        # Create backup of original file
        backup_path = pdf_path.with_suffix('.pdf.bak')
        pdf_path.rename(backup_path)
        
        # Write the updated PDF
        with open(str(pdf_path), 'wb') as output_file:
            writer.write(output_file)
        
        # Remove backup if successful
        backup_path.unlink()
        
        print(f"✓ Updated: {pdf_path.name} - Title set to: '{filename_without_ext}'")
        return True
        
    except Exception as e:
        print(f"✗ Error updating {pdf_path.name}: {str(e)}")
        
        # Restore from backup if it exists
        backup_path = pdf_path.with_suffix('.pdf.bak')
        if backup_path.exists():
            if pdf_path.exists():
                pdf_path.unlink()
            backup_path.rename(pdf_path)
            
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Update PDF Title metadata to match filename for all PDFs in a directory'
    )
    parser.add_argument(
        '--directory', '-d',
        default='./docs',
        help='Directory containing PDF files (default: ./docs)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    
    args = parser.parse_args()
    
    # Convert to Path object
    docs_dir = Path(args.directory)
    
    # Check if directory exists
    if not docs_dir.exists():
        print(f"Error: Directory '{docs_dir}' does not exist")
        return 1
    
    if not docs_dir.is_dir():
        print(f"Error: '{docs_dir}' is not a directory")
        return 1
    
    # Find all PDF files (including subdirectories)
    pdf_files = list(docs_dir.glob('**/*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in '{docs_dir}'")
        return 0
    
    print(f"Found {len(pdf_files)} PDF file(s) in '{docs_dir}'")
    print("-" * 50)
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print("-" * 50)
        for pdf_path in pdf_files:
            print(f"Would update: {pdf_path.name} -> Title: '{pdf_path.stem}'")
        return 0
    
    # Process each PDF
    successful = 0
    failed = 0
    
    for pdf_path in pdf_files:
        if update_pdf_title(pdf_path):
            successful += 1
        else:
            failed += 1
    
    # Summary
    print("-" * 50)
    print(f"Summary: {successful} successful, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())