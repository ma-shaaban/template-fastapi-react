# Feature routers live here — one APIRouter module per feature area, e.g.:
#
#   # backend/app/routers/tasks.py
#   from fastapi import APIRouter
#   router = APIRouter(prefix="/api/tasks", tags=["tasks"])
#
#   @router.get("")
#   def list_tasks(): ...
#
# Register each router in app/main.py ABOVE the SPA catch-all:
#
#   from app.routers import tasks
#   app.include_router(tasks.router)
#
# Don't grow main.py into a single-file app — a real app in one file is
# unmaintainable. Business logic the routes call goes in app/services/.
