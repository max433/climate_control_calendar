"""
HTTP Views for Climate Control Calendar dashboard.

Serves dashboard HTML page with embedded JavaScript.
"""
from __future__ import annotations

import logging
import os

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)


class DashboardView(HomeAssistantView):
    """View to serve Climate Control Calendar dashboard."""

    url = "/api/climate_control_calendar/dashboard"
    name = "api:climate_control_calendar:dashboard"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Serve dashboard HTML page."""
        # Read JS file
        integration_dir = os.path.dirname(__file__)
        frontend_dir = os.path.join(integration_dir, "frontend")
        panel_js_path = os.path.join(frontend_dir, "climate-control-panel.js")

        try:
            with open(panel_js_path, "r", encoding="utf-8") as f:
                panel_js_content = f.read()
        except Exception as err:
            _LOGGER.error("Failed to read panel JS file: %s", err)
            return web.Response(
                text="Error loading dashboard", status=500
            )

        # Build complete HTML page
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Climate Control Calendar Dashboard</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--primary-background-color, #fafafa);
            color: var(--primary-text-color, #212121);
        }}

        /* Home Assistant theme CSS variables */
        :root {{
            --primary-color: #03a9f4;
            --accent-color: #ff9800;
            --primary-background-color: #fafafa;
            --card-background-color: #ffffff;
            --primary-text-color: #212121;
            --secondary-text-color: #727272;
            --disabled-text-color: #bdbdbd;
            --divider-color: rgba(0, 0, 0, 0.12);
            --success-color: #4caf50;
            --warning-color: #ff9800;
            --error-color: #f44336;
            --info-color: #2196f3;
            --ha-card-box-shadow: 0 2px 2px 0 rgba(0,0,0,0.14), 0 1px 5px 0 rgba(0,0,0,0.12), 0 3px 1px -2px rgba(0,0,0,0.2);
        }}

        /* Dark theme (auto-detect) */
        @media (prefers-color-scheme: dark) {{
            :root {{
                --primary-background-color: #111111;
                --card-background-color: #1c1c1c;
                --primary-text-color: #e1e1e1;
                --secondary-text-color: #9b9b9b;
                --disabled-text-color: #6f6f6f;
                --divider-color: rgba(255, 255, 255, 0.12);
            }}
        }}

        /* HA Card styles */
        ha-card {{
            background: var(--card-background-color);
            border-radius: 8px;
            box-shadow: var(--ha-card-box-shadow);
            padding: 16px;
            margin-bottom: 16px;
        }}

        .card-content {{
            padding: 0;
        }}

        .card-content h2 {{
            margin-top: 0;
            margin-bottom: 16px;
            font-size: 20px;
            font-weight: 500;
        }}

        .card-content h3 {{
            margin-top: 16px;
            margin-bottom: 8px;
            font-size: 16px;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <!-- Dashboard container -->
    <climate-control-panel id="dashboard"></climate-control-panel>

    <!-- Embedded JavaScript -->
    <script>
{panel_js_content}

// Initialize dashboard after DOM load
document.addEventListener('DOMContentLoaded', async () => {{
    const dashboard = document.getElementById('dashboard');

    // Get Home Assistant connection
    // When loaded in iframe panel, parent window has Home Assistant context
    const getHass = () => {{
        if (window.parent && window.parent.hassConnection) {{
            return window.parent.hassConnection;
        }}
        // Fallback: try to get from parent hass object
        if (window.parent && window.parent.hass) {{
            return window.parent.hass;
        }}
        return null;
    }};

    // Wait for hass to be available
    const waitForHass = () => {{
        return new Promise((resolve) => {{
            const check = () => {{
                const hass = getHass();
                if (hass) {{
                    resolve(hass);
                }} else {{
                    setTimeout(check, 100);
                }}
            }};
            check();
        }});
    }};

    try {{
        const hass = await waitForHass();
        dashboard.hass = hass;

        // Listen for hass updates from parent
        window.addEventListener('message', (event) => {{
            if (event.data.type === 'hass-update') {{
                dashboard.hass = event.data.hass;
            }}
        }});

        console.log('Climate Control Calendar Dashboard initialized');
    }} catch (err) {{
        console.error('Failed to initialize dashboard:', err);
        dashboard.innerHTML = '<div style="padding: 48px; text-align: center; color: var(--error-color);">Failed to connect to Home Assistant</div>';
    }}
}});
    </script>
</body>
</html>
"""

        return web.Response(
            text=html_content,
            content_type="text/html",
            charset="utf-8",
        )
