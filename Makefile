dev:
	KINGPI_ENV=dev docker compose up --build

dev-multi:
	KINGPI_ENV=dev-multi docker compose up --build

prod:
	KINGPI_ENV=prod docker compose up --build -d

infra:
	docker compose up postgres redis -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose run --rm app pytest

.PHONY: dev dev-multi prod infra down logs test
