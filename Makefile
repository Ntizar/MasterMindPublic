.PHONY: demo help install

help:
	@echo "MasterMindPublic — Comandos disponibles"
	@echo ""
	@echo "  demo         Ejecuta la demo completa (indexación, recuperación, routing)"
	@echo "  install      Instala las dependencias de Python"
	@echo "  doctor       Ejecuta el chequeo de salud del sistema"
	@echo "  clean        Elimina archivos temporales y cachés"
	@echo ""

demo:
	@python scripts/demo.py

install:
	@pip install -r requirements.txt

clean:
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .chromadb/ 2>/dev/null || true