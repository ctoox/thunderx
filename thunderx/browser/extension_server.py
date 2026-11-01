"""Browser extension integration server"""

import asyncio
import json
from typing import Optional, Callable, Dict, Any
from aiohttp import web
from ..utils.logger import setup_logger


class ExtensionServer:
    """HTTP server for browser extension communication"""

    def __init__(self, port: int = 9527):
        self.logger = setup_logger("browser")
        self.port = port
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._callbacks: Dict[str, Callable] = {}

    async def start(self):
        """Start the extension server"""
        self._app = web.Application()
        self._setup_routes()
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        site = web.TCPSite(self._runner, "127.0.0.1", self.port)
        await site.start()
        
        self.logger.info(f"Browser extension server started on port {self.port}")

    async def stop(self):
        """Stop the extension server"""
        if self._runner:
            await self._runner.cleanup()
        self.logger.info("Browser extension server stopped")

    def _setup_routes(self):
        """Setup HTTP routes"""
        self._app.router.add_post("/api/download", self._handle_download)
        self._app.router.add_post("/api/batch", self._handle_batch_download)
        self._app.router.add_get("/api/tasks", self._handle_get_tasks)
        self._app.router.add_post("/api/tasks/{task_id}/pause", self._handle_pause_task)
        self._app.router.add_post("/api/tasks/{task_id}/resume", self._handle_resume_task)
        self._app.router.add_delete("/api/tasks/{task_id}", self._handle_delete_task)
        self._app.router.add_get("/api/status", self._handle_status)
        
        # CORS support
        self._app.middlewares.append(self._cors_middleware)

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        """CORS middleware for browser extension"""
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)
        
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    async def _handle_download(self, request: web.Request) -> web.Response:
        """Handle download request from extension"""
        try:
            data = await request.json()
            url = data.get("url")
            filename = data.get("filename")
            headers = data.get("headers", {})
            
            if not url:
                return web.json_response({"error": "URL required"}, status=400)
            
            # Call registered callback
            if "add_download" in self._callbacks:
                result = await self._callbacks["add_download"](url, filename, headers)
                return web.json_response({"success": True, "task_id": result})
            
            return web.json_response({"error": "Handler not registered"}, status=500)
            
        except Exception as e:
            self.logger.error(f"Download handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_batch_download(self, request: web.Request) -> web.Response:
        """Handle batch download request"""
        try:
            data = await request.json()
            urls = data.get("urls", [])
            
            if not urls:
                return web.json_response({"error": "URLs required"}, status=400)
            
            # Call registered callback
            if "batch_download" in self._callbacks:
                results = await self._callbacks["batch_download"](urls)
                return web.json_response({"success": True, "task_ids": results})
            
            return web.json_response({"error": "Handler not registered"}, status=500)
            
        except Exception as e:
            self.logger.error(f"Batch handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_get_tasks(self, request: web.Request) -> web.Response:
        """Get all download tasks"""
        if "get_tasks" in self._callbacks:
            tasks = await self._callbacks["get_tasks"]()
            return web.json_response({"tasks": tasks})
        return web.json_response({"tasks": []})

    async def _handle_pause_task(self, request: web.Request) -> web.Response:
        """Pause a download task"""
        task_id = request.match_info["task_id"]
        if "pause_task" in self._callbacks:
            await self._callbacks["pause_task"](task_id)
            return web.json_response({"success": True})
        return web.json_response({"error": "Handler not registered"}, status=500)

    async def _handle_resume_task(self, request: web.Request) -> web.Response:
        """Resume a download task"""
        task_id = request.match_info["task_id"]
        if "resume_task" in self._callbacks:
            await self._callbacks["resume_task"](task_id)
            return web.json_response({"success": True})
        return web.json_response({"error": "Handler not registered"}, status=500)

    async def _handle_delete_task(self, request: web.Request) -> web.Response:
        """Delete a download task"""
        task_id = request.match_info["task_id"]
        if "delete_task" in self._callbacks:
            await self._callbacks["delete_task"](task_id)
            return web.json_response({"success": True})
        return web.json_response({"error": "Handler not registered"}, status=500)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Get server status"""
        return web.json_response({
            "status": "running",
            "version": "1.0.0",
        })

    def on(self, event: str, callback: Callable):
        """Register event callback"""
        self._callbacks[event] = callback

    def get_extension_manifest(self) -> Dict[str, Any]:
        """Get browser extension manifest"""
        return {
            "manifest_version": 3,
            "name": "ThunderX Download Manager",
            "version": "1.0.0",
            "description": "Integrate with ThunderX download manager",
            "permissions": [
                "downloads",
                "contextMenus",
                "activeTab",
            ],
            "host_permissions": [
                "<all_urls>",
            ],
            "background": {
                "service_worker": "background.js",
            },
            "action": {
                "default_popup": "popup.html",
                "default_icon": {
                    "16": "icons/icon16.png",
                    "48": "icons/icon48.png",
                    "128": "icons/icon128.png",
                },
            },
        }
