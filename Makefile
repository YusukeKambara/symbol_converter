VERSION := 0.0.3
IMAGE_NAME := symbol-converter
SERVICE_NAME := symbol-converter
PROJECT_NAME := develop
TOPIC_NAME := ticker-symbols


$(eval REGION := $(shell gcloud config get-value compute/region))
$(eval PROJECT_ID := $(shell gcloud projects list --filter=$(PROJECT_NAME) --format="value(projectId)"))

.PHONY: build, deploy

# Common commands
build:
	gcloud builds submit --tag gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(VERSION) \
						 --project $(PROJECT_ID)

deploy:
	@echo "################################################"
	@echo [Topic Existence Check]
	@echo "################################################"
	$(eval CMD_RESULT := $(shell gcloud pubsub topics list --format="flattened" --filter="name=projects/$(PROJECT_ID)/topics/$(TOPIC_NAME)"))

	@if [ -z "$(CMD_RESULT)" ]; then \
		gcloud pubsub topics create $(TOPIC_NAME); \
	else \
		echo "$(TOPIC_NAME)" already exists; \
	fi

	@echo "################################################"
	@echo [Deploy Cloud Run]
	@echo "################################################"
	gcloud run deploy $(SERVICE_NAME) --image gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(VERSION) \
									--platform managed \
									--allow-unauthenticated \
									--set-env-vars=GOOGLE_CLOUD_PROJECT=$(PROJECT_ID) \
									--set-env-vars=PUBSUB_TOPIC=$(TOPIC_NAME) \
									--region $(REGION) \
									--project $(PROJECT_ID)
