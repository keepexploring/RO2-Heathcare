# Build & start the full stack
up:
	docker compose up --build

# Stop & remove containers
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Run MQTT test publisher
publish:
	source .venv/bin/activate && python3 publish_test.py

# Database migrations
migrate:
	source .venv/bin/activate && export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/sensordb" && alembic upgrade head

# Generate new migration
migration:
	source .venv/bin/activate && export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/sensordb" && alembic revision --autogenerate -m "$(MESSAGE)"

# Deploy: build, migrate, and start
deploy:
	docker compose up --build -d
	sleep 10
	make migrate
	@echo "🚀 Deployment complete! Dashboard: http://localhost:5006/dashboard"

# Generate password hash for .env file
hash:
	@echo "Enter password to hash:"
	@read -s password; python3 -c "import bcrypt; print('Hashed password:', bcrypt.hashpw('$$password'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))"

# Convenience: start stack and publisher in separate terminal windows (requires tmux)
start:
	tmux new-session -d -s sensor_stack 'make up'
	tmux split-window -h 'make publish'
	tmux attach -t sensor_stack