# Packaging targets. Application code: biblecli/. Zipapp build: scripts/build_zipapp.sh

.PHONY: zipapp clean-zipapp

zipapp:
	./scripts/build_zipapp.sh

clean-zipapp:
	rm -rf .zipapp_stage dist/biblecli
