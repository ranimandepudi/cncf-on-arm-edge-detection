# Get the currently used golang install path (in GOPATH/bin, unless GOBIN is set)
ifeq (,$(shell go env GOBIN))
GOBIN=$(shell go env GOPATH)/bin
else
GOBIN=$(shell go env GOBIN)
endif

VERSION 	?= main
GIT_COMMIT  ?= $(shell git rev-list -1 HEAD)
CONTAINER_IMAGE ?= docker.io/jkremser/object-detection-api
CONTAINER_TOOL ?= docker

.PHONY: all
all: help

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ General

.PHONY: build-image-multiarch
build-image-multiarch: ## Builds the container image for amd and arm arch and pushes them to container registry.
	@$(call say,Build container image $(CONTAINER_IMAGE))
	$(CONTAINER_TOOL) buildx build . --push --platform linux/amd64,linux/arm64 -t $(CONTAINER_IMAGE):$(VERSION) --build-arg VERSION=$(VERSION) --build-arg GIT_COMMIT=$(GIT_COMMIT)

ifndef NO_COLOR
YELLOW=\033[0;33m
# no color
NC=\033[0m
endif

define say
echo -e "\n$(shell echo "$1  " | sed s/./=/g)\n $(YELLOW)$1$(NC)\n$(shell echo "$1  " | sed s/./=/g)"
endef
