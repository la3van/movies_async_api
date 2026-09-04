SENTRY_VERSION ?= 23.12.1
SENTRY_DIR := infrastructure/sentry-self-hosted

.PHONY: sentry-install sentry-up sentry-down up down ps

sentry-install:
	@test ! -e "$(SENTRY_DIR)" || { echo "$(SENTRY_DIR) already exists"; exit 1; }
	git clone --branch "$(SENTRY_VERSION)" --depth 1 \
		https://github.com/getsentry/self-hosted.git "$(SENTRY_DIR)"
	cd "$(SENTRY_DIR)" && ./install.sh

sentry-up:
	@test -f "$(SENTRY_DIR)/docker-compose.yml" || { \
		echo "Run 'make sentry-install' first"; exit 1; \
	}
	cd "$(SENTRY_DIR)" && docker compose up -d

sentry-down:
	@if test -f "$(SENTRY_DIR)/docker-compose.yml"; then \
		cd "$(SENTRY_DIR)" && docker compose down; \
	fi

up: sentry-up
	docker compose up -d

down:
	docker compose down
	$(MAKE) sentry-down

ps:
	docker compose ps
	@if test -f "$(SENTRY_DIR)/docker-compose.yml"; then \
		cd "$(SENTRY_DIR)" && docker compose ps; \
	fi
