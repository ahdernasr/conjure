# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

# Stage 2: Node runtime (we copy binaries from here)
FROM node:20-slim AS node-bin

# Stage 3: Production image
FROM python:3.12-slim

# Copy Node.js + npm from the node image (needed for vite builds of generated apps)
COPY --from=node-bin /usr/local/bin/node /usr/local/bin/node
COPY --from=node-bin /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Install template node_modules (used for building generated apps)
RUN cd app/template && npm ci

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static

# Create apps directory
RUN mkdir -p apps

EXPOSE 8001

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
