# Paquete de la Lambda: código de back/ (solo biblioteca estándar + boto3 del runtime) y archivos de front/.
# `sam build` invoca este objetivo (BuildMethod: makefile en template.yaml).
build-AppFunction:
	cp back/app.py "$(ARTIFACTS_DIR)/"
	cp -r back/aulalista "$(ARTIFACTS_DIR)/aulalista"
	cp -r front "$(ARTIFACTS_DIR)/front"
	find "$(ARTIFACTS_DIR)" -name "__pycache__" -type d -prune -exec rm -rf {} +

test:
	python3 -m unittest discover -s tests

.PHONY: build-AppFunction test
