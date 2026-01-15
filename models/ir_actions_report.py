import io
import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import weasyprint
    from weasyprint import HTML, CSS
except ImportError:
    weasyprint = None
    _logger.warning(
        "WeasyPrint python library not installed. PDF generation via WeasyPrint will fail."
    )


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _run_wkhtmltopdf(
        self,
        bodies,
        report_ref,
        header=None,
        footer=None,
        landscape=False,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        """
        Override the default wkhtmltopdf runner to use WeasyPrint.
        This can be controlled globally or per-module via system settings.
        """
        ICP = self.env["ir.config_parameter"].sudo()

        # Check if WeasyPrint is enabled globally
        weasyprint_enabled = ICP.get_param("report_weasyprint.enabled", False)

        # Get module for this report
        report_module = self._get_report_module(report_ref)

        # Check if this module is in allowed list (if globally disabled)
        allowed_modules = (
            ICP.get_param("report_weasyprint.allowed_modules", "").split(",")
            if ICP.get_param("report_weasyprint.allowed_modules")
            else []
        )
        # Check if this module is in blocked list (if globally enabled)
        blocked_modules = (
            ICP.get_param("report_weasyprint.blocked_modules", "").split(",")
            if ICP.get_param("report_weasyprint.blocked_modules")
            else []
        )

        # Determine if we should use WeasyPrint
        use_weasyprint = False
        if weasyprint_enabled:
            # Globally enabled, check if blocked
            use_weasyprint = report_module not in blocked_modules
        else:
            # Globally disabled, check if allowed
            use_weasyprint = report_module in allowed_modules

        if not use_weasyprint or not weasyprint:
            if not weasyprint:
                _logger.warning(
                    "WeasyPrint not found, falling back to original wkhtmltopdf execution."
                )
            else:
                _logger.info(
                    "WeasyPrint is not enabled for this report (module: %s). Using wkhtmltopdf instead.",
                    report_module,
                )
            return super(IrActionsReport, self)._run_wkhtmltopdf(
                bodies,
                report_ref,
                header,
                footer,
                landscape,
                specific_paperformat_args,
                set_viewport_size,
            )

        _logger.info(
            "Generating PDF with WeasyPrint for report: %s (module: %s)",
            report_ref,
            report_module,
        )

        # 1. Resolve Base URL for assets
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base_url:
            base_url = "http://127.0.0.1:8069"

        docs = []

        # 2. Parse Margins from specific_paperformat_args
        margin_style = ""
        if specific_paperformat_args:

            def get_arg(key):
                val = specific_paperformat_args.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
                return None

            top = get_arg("--margin-top")
            bottom = get_arg("--margin-bottom")
            left = get_arg("--margin-left")
            right = get_arg("--margin-right")
            page_width = get_arg("--page-width")
            page_height = get_arg("--page-height")

            rules = []
            if top is not None:
                rules.append(f"margin-top: {top}mm;")
            if bottom is not None:
                rules.append(f"margin-bottom: {bottom}mm;")
            if left is not None:
                rules.append(f"margin-left: {left}mm;")
            if right is not None:
                rules.append(f"margin-right: {right}mm;")

            if page_width is not None and page_height is not None:
                rules.append(f"size: {page_width}mm {page_height}mm;")
            elif landscape:
                rules.append("size: landscape;")

            if rules:
                margin_style = "@page { " + " ".join(rules) + " }"

        # 3. Helper to decode bytes to str
        def to_str(content):
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return content or ""

        header_str = to_str(header)
        footer_str = to_str(footer)

        for body in bodies:
            body_str = to_str(body)
            html_parts = []
            css_rules = []

            # 5. Bootstrap/Odoo Compatibility Fixes
            # Moved to the top to serve as a baseline/reset.
            compatibility_css = """
                * { 
                    -webkit-print-color-adjust: exact !important; 
                    print-color-adjust: exact !important; 
                    box-sizing: border-box !important;
                }
                html, body {
                    height: auto !important;
                    overflow: visible !important;
                }
                .container { 
                    width: 100% !important; 
                    max-width: none !important; 
                    padding: 0 !important; 
                    margin: 0 !important; 
                }
                tr { break-inside: avoid; page-break-inside: avoid; }
                @page { -weasy-print: yes; size: auto; margin: 0; }
            """
            css_rules.append(compatibility_css)

            if margin_style:
                css_rules.append(margin_style)

            # 4. Handle Header/Footer with CSS Paged Media
            if header_str:
                html_parts.append(
                    f'<div id="header-content" style="position: running(header);">{header_str}</div>'
                )
                css_rules.append(
                    "@page { @top-center { content: element(header); width: 100%; } }"
                )

            if footer_str:
                html_parts.append(
                    f'<div id="footer-content" style="position: running(footer);">{footer_str}</div>'
                )
                css_rules.append(
                    "@page { @bottom-center { content: element(footer); width: 100%; } }"
                )

            html_parts.append(body_str)

            full_html = f"""
                <!DOCTYPE html>
                <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            html, body {{ width: 100%; margin: 0; padding: 0; }}
                            {"\n".join(css_rules)}
                        </style>
                    </head>
                    <body class="container">
                        {"".join(html_parts)}
                    </body>
                </html>
            """

            try:
                doc = HTML(string=full_html, base_url=base_url).render()
                docs.append(doc)
            except Exception as e:
                _logger.error("WeasyPrint rendering failed: %s", e, exc_info=True)
                raise UserError(_("WeasyPrint rendering failed: %s") % str(e))

        if not docs:
            return b""

        if len(docs) > 1:
            all_pages = []
            for d in docs:
                all_pages.extend(d.pages)
            final_doc = docs[0].copy(all_pages)
        else:
            final_doc = docs[0]

        buffer = io.BytesIO()
        final_doc.write_pdf(target=buffer)
        return buffer.getvalue()

    def _get_report_module(self, report_ref):
        """Extract the module name from a report reference."""
        if isinstance(report_ref, str):
            if "." in report_ref:
                return report_ref.split(".")[0]
        # Fallback: try to find the report record
        report = (
            self.search([("report_name", "=", report_ref)], limit=1)
            if report_ref
            else self
        )
        if report and report.module:
            return report.module
        # If we can't determine, assume unknown
        return "unknown"
