.PHONY: up down restart logs status shell db

up:
.env docker compose up -d --build

down:
.env docker compose down

restart: down up

logs:
.env docker compose logs -f

status:
.env docker compose ps

shell:
.env docker exec -it lalafo-bot bash

db:
.env docker exec -it lalafo-bot sqlite3 bot.db
