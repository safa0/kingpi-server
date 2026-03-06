dev:
	docker compose --profile dev up --build

dev-multi:
	docker compose --profile dev-multi up --build

prod:
	docker compose --profile prod up --build -d

infra:
	docker compose up postgres redis -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose --profile dev run --rm app-dev pytest

.PHONY: dev dev-multi prod infra down logs test
