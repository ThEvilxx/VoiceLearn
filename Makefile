PYTHON := python
PIP := pip

.PHONY: dev prod install install-backend install-frontend lint check clean

# 开发模式：前后端同时启动
dev:
	@echo "Starting backend (port 8000) + frontend (port 5173)..."
	@cd backend && $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
	@cd frontend && npm run dev &
	@wait

# 生产模式：仅后端（serve 前端静态文件）
prod:
	@echo "Building frontend..."
	@cd frontend && npm run build
	@echo "Starting server at http://127.0.0.1:8000"
	@cd backend && $(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 安装所有依赖
install: install-backend install-frontend

install-backend:
	cd backend && $(PIP) install -r requirements.txt

install-frontend:
	cd frontend && npm install

# 代码检查
lint:
	cd frontend && npm run lint

check:
	cd backend && $(PYTHON) -m ruff check app/
	cd backend && $(PYTHON) -m mypy app/ --ignore-missing-imports

# 清理
clean:
	-rm -rf backend/__pycache__ backend/app/**/\__pycache__
	-rm -rf frontend/dist

# ============================================================
# Windows 用户注意：
# 如果 make 命令不可用，请手动执行以下命令：
#
# 安装：
#   cd backend && pip install -r requirements.txt
#   cd frontend && npm install
#
# 启动开发模式（需要两个终端）：
#   终端 1: cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
#   终端 2: cd frontend && npm run dev
#
# 启动生产模式：
#   cd frontend && npm run build
#   cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# ============================================================
