"""
Keep-alive web server for Replit free hosting.
UptimeRobot pings /ping every 5 minutes to prevent sleep.
"""

from aiohttp import web
import asyncio
import logging

logger = logging.getLogger(__name__)


async def handle_ping(request):
    return web.Response(text="OK", status=200)


async def handle_root(request):
    return web.Response(
        text="<h2>🤖 Marlboro Bot — Running</h2><p>Status: <b style='color:green'>ONLINE</b></p>",
        content_type="text/html",
        status=200
    )


async def start_keep_alive(port: int = 8000):
    """Start the keep-alive HTTP server in the background."""
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/ping", handle_ping)
    app.router.add_get("/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Keep-alive server started on port %d", port)
