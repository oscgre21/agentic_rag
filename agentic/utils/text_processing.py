"""
Utilidades para procesamiento de texto.
Siguiendo el principio de Single Responsibility.
"""

import re
from typing import Tuple, List
from ..models.schemas import DocumentReference


def remove_think_blocks(text: str) -> str:
    """
    Remueve todos los bloques <think></think> del texto.
    """
    pattern = r'<think>.*?</think>'
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    return cleaned_text.strip()


def extract_document_references(text: str) -> Tuple[str, List[DocumentReference]]:
    """
    Extrae las referencias de documentos del texto y devuelve el texto limpio y las referencias.
    Busca patrones como [Document.pdf - Page X] o REFERENCES: ...
    Soporta tanto formato en inglés como español para compatibilidad.
    """
    references_dict = {}
    clean_text = text
    
    # Patrón para encontrar referencias
    pattern = r'\[([^]]*\.pdf)\s*[-–]\s*(?:[Pp]ág(?:ina)?\.?|[Pp]age)\s*(\d+)\]'
    matches = re.findall(pattern, text)
    
    for doc_name, page in matches:
        doc_name = doc_name.strip()
        page_num = int(page)
        
        if doc_name not in references_dict:
            references_dict[doc_name] = []
        if page_num not in references_dict[doc_name]:
            references_dict[doc_name].append(page_num)
    
    # Buscar sección de REFERENCES
    referencias_section = re.search(r'REFERENCES:\s*(.+?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
    if referencias_section:
        refs_text = referencias_section.group(1)
        clean_text = text[:referencias_section.start()].strip()
        
        ref_lines = refs_text.strip().split('\n')
        for line in ref_lines:
            matches_in_line = re.findall(pattern, line)
            for doc_name, page in matches_in_line:
                doc_name = doc_name.strip()
                page_num = int(page)
                
                if doc_name not in references_dict:
                    references_dict[doc_name] = []
                if page_num not in references_dict[doc_name]:
                    references_dict[doc_name].append(page_num)
    
    # Convertir a lista de DocumentReference
    document_references = []
    for doc_name, pages in references_dict.items():
        document_references.append(DocumentReference(
            document_name=doc_name,
            pages=sorted(pages)
        ))
    
    return clean_text, document_references


def format_conversation_history(messages: List) -> str:
    """
    Format conversation history for context
    """
    if not messages:
        return ""
    
    history = "Historial de conversación:\n"
    for msg in messages[-10:]:  # Últimos 10 mensajes para contexto
        role = "Usuario" if msg.role == "user" else "Asistente"
        history += f"{role}: {msg.content}\n"
    
    return history