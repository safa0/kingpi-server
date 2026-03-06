dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

infra:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up postgres redis -d

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

down-prod:
	DATABASE_URL=$${DATABASE_URL:?DATABASE_URL must be set} docker compose -f docker-compose.yml -f docker-compose.prod.yml down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

test:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm app pytest

.PHONY: dev prod infra down down-prod logs test
