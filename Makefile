# Paquetes de las Lambdas (`sam build` invoca estos objetivos: BuildMethod makefile en template.yaml).
# Solo biblioteca estándar + boto3 del runtime. Se excluyen cachés y bases de datos locales.
build-AppFunction:
	cp back/app.py "$(ARTIFACTS_DIR)/"
	cp -r back/aulalista "$(ARTIFACTS_DIR)/aulalista"
	cp -r front "$(ARTIFACTS_DIR)/front"
	find "$(ARTIFACTS_DIR)" -name "__pycache__" -type d -prune -exec rm -rf {} +
	find "$(ARTIFACTS_DIR)" \( -name "*.db" -o -name "*.pyc" \) -delete

build-JobWorkerFunction:
	cp back/worker.py "$(ARTIFACTS_DIR)/"
	cp -r back/aulalista "$(ARTIFACTS_DIR)/aulalista"
	find "$(ARTIFACTS_DIR)" -name "__pycache__" -type d -prune -exec rm -rf {} +
	find "$(ARTIFACTS_DIR)" \( -name "*.db" -o -name "*.pyc" \) -delete

test:
	python3 -m unittest discover -s tests

.PHONY: build-AppFunction build-JobWorkerFunction test
