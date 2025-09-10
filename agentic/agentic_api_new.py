#!/usr/bin/env python
"""
Archivo de compatibilidad para mantener el funcionamiento del archivo original agentic_api.py
Este archivo simplemente importa y ejecuta la nueva aplicación refactorizada.
"""

import warnings
warnings.warn(
    "agentic_api.py está deprecado. Use 'python -m agentic.app' o importe desde agentic.app",
    DeprecationWarning,
    stacklevel=2
)

# Importar la app refactorizada
from app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)