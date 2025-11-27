up-nebula:
	cd nebula-docker-compose
	docker compose up -d
	cd ../

log-nebula:
	cd nebula-docker-compose
	docker compose logs -f --tail 50

build:
	docker compose build

down:
	docker compose down

up:
	docker compose up -d

up-build:
	docker compose up --build -d

create-network:
	docker network create code-review-external-network
