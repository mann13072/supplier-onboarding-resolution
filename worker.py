from urllib.parse import urlparse
import re

from workers import DurableObject, Response, WorkerEntrypoint

from app.api import create_app
from app.cloudflare_store import CloudflareStore


class DemoWorkspace(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.app = create_app(store=CloudflareStore(ctx.storage), serve_frontend=False)

    async def fetch(self, request):
        from workers import asgi

        return await asgi.fetch(self.app, request, self.env, self.ctx)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if not urlparse(request.url).path.startswith("/api/"):
            return Response("Not found", status=404)
        session = request.headers.get("X-Demo-Session") or "portfolio-demo-v1"
        if not re.fullmatch(r"[A-Za-z0-9-]{16,64}", session):
            return Response("Invalid demo session", status=400)
        workspace = self.env.DEMO_WORKSPACES.get(self.env.DEMO_WORKSPACES.idFromName(session))
        return await workspace.fetch(request.js_object)
