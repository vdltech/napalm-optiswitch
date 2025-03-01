# vim:ft=make:noexpandtab:
.PHONY: format
.DEFAULT_GOAL := help

format: ## Run python formatter
	black --target-version py39 --line-length 100 .

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
