# WeasyPrint Report Engine

This Odoo module replaces the default `wkhtmltopdf` PDF generation engine with **WeasyPrint**.

WeasyPrint offers better support for modern CSS (including Flexbox and Grid) and avoids the dependency on the deprecated `wkhtmltopdf` binary.

## Credits

Based on the work by [Holger Brunn (hbrunn)](https://github.com/hbrunn) and the [OCA reporting-engine](https://github.com/OCA/reporting-engine) community.

## Prerequisites (Both Docker & Non-Docker)

### 1. System Dependencies
The host machine (or container) must have the following system libraries installed:

- **Debian/Ubuntu:**
  ```bash
  sudo apt-get update && sudo apt-get install -y \
      python3-pip python3-cffi python3-brotli \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
      libjpeg-dev libopenjp2-7-dev libmemcached-dev zlib1g-dev
  ```

### 2. Python Dependencies
Install the `weasyprint` library in your Odoo environment:

```bash
pip3 install weasyprint
```

---

## Installation

### Option A: Docker Setup (Recommended)

1.  **Dockerfile:** Add the dependencies to your custom Odoo image:
    ```dockerfile
    FROM odoo:18.0
    USER root
    RUN apt-get update && apt-get install -y [system-deps-above]
    RUN pip3 install weasyprint --break-system-packages
    USER odoo
    ```

2.  **Mounting:** Add the module to your `docker-compose.yml`:
    ```yaml
    services:
      odoo:
        volumes:
          - ./report_weasyprint:/mnt/extra-addons/report_weasyprint
    ```

### Option B: Local / Non-Docker Setup

1.  **Add to Path:** Copy the `report_weasyprint` folder into one of your Odoo `addons_path` directories (e.g., `/opt/odoo/additional_addons`).
2.  **Update Config:** Ensure your `odoo.conf` reflects the path:
    ```ini
    addons_path = /opt/odoo/odoo/addons,/opt/odoo/additional_addons
    ```

---

## Activation

1.  Restart your Odoo server/container.
2.  Log in as Administrator and activate **Developer Mode**.
3.  Go to **Apps** -> **Update Apps List**.
4.  Search for `WeasyPrint Report Engine` and click **Activate**.

## Troubleshooting
- **Missing Images/CSS:** Ensure `web.base.url` in System Parameters is correctly set and reachable by the Odoo server.
- **Log Errors:** Check for `WeasyPrint rendering failed` in your server logs.
