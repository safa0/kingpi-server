dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.prod.yml down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.prod.yml logs -f

test:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm app pytest

.PHONY: dev prod down logs test
