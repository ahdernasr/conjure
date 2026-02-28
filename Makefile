.PHONY: dev setup backend frontend clean

dev: setup
	@echo "Starting Conjure..."
	@echo "  Frontend → http://localhost:5173"
	@echo "  Backend  → http://localhost:8001"
	@echo "  Press Ctrl+C to stop"
	@bash dev.sh

setup: backend/venv frontend/node_modules

backend/venv:
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt -q

frontend/node_modules:
	cd frontend && npm install --silent

backend:
	cd backend && ./venv/bin/python run.py

frontend:
	cd frontend && npx vite --host

clean:
	rm -rf backend/venv frontend/node_modules frontend/dist backend/conjure.db
