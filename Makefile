VERSION := 0.0.1
IMAGE_NAME := get_ticker_symbol
SERVICE_NAME := get-ticker-symbol
PROJECT_NAME := develop
TOPIC_NAME := jp_company_names


$(eval REGION := $(shell gcloud config get-value compute/region))
$(eval PROJECT_ID := $(shell gcloud projects list --filter=$(PROJECT_NAME) --format="value(projectId)"))

.PHONY: build, deploy

# Common commands
build:
	gcloud builds submit --tag gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(VERSION) \
						 --project $(PROJECT_ID)

deploy:
	gcloud run deploy $(SERVICE_NAME) --image gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(VERSION) \
									--platform managed \
									--set-env-vars=GOOGLE_CLOUD_PROJECT=$(PROJECT_ID) \
									--set-env-vars=PUBSUB_TOPIC=$(TOPIC_NAME) \
									--region $(REGION) \
									--project $(PROJECT_ID)
