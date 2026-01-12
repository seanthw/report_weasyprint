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


def _render_qweb_pdf(
    self,
    report_ref,
    docids,
    data=None,
):
    """
    Override the main PDF rendering method to use WeasyPrint.
    """
    if not weasyprint:
        _logger.warning("WeasyPrint not found, falling back to original PDF rendering.")
        return super(IrActionsReport, self)._render_qweb_pdf(report_ref, docids, data)

    _logger.info("Generating PDF with WeasyPrint for report: %s", report_ref)

    # 1. Resolve Base URL for assets
    # In Docker, localhost refers to the container. Odoo usually listens on 8069.
    # We prefer the frozen web.base.url, but ensure it's reachable.
    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
    if not base_url:
        base_url = "http://127.0.0.1:8069"

    docs = []

    # 2. Parse Margins from paperformat
    # Get the report's paperformat
    report = self.env["ir.actions.report"].browse(report_ref)
    paperformat = report.paperformat_id
    margin_style = ""
    if paperformat:
        top = paperformat.margin_top
        bottom = paperformat.margin_bottom
        left = paperformat.margin_left
        right = paperformat.margin_right

        # Extract explicit page size if present (for 'custom' formats)
        page_width = paperformat.page_width
        page_height = paperformat.page_height

        rules = []
        if top is not None:
            rules.append(f"margin-top: {top}mm;")
        if bottom is not None:
            rules.append(f"margin-bottom: {bottom}mm;")
        if left is not None:
            rules.append(f"margin-left: {left}mm;")
        if right is not None:
            rules.append(f"margin-right: {right}mm;")

        # Handle Page Size
        if page_width is not None and page_height is not None:
            rules.append(f"size: {page_width}mm {page_height}mm;")

        if rules:
            margin_style = "@page { " + " ".join(rules) + " }"

    # 3. Helper to decode bytes to str
    def to_str(content):
        if isinstance(content, bytes):
            return content.decode("utf-8")
        return content or ""

    # 4. Get HTML content
    html_content = self._render_qweb_html(report_ref, docids, data=data)
    html_str = to_str(html_content)

    # 5. WeasyPrint compatibility fixes
    compatibility_css = """
            /* Ensure background colors print */
            * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
            /* Bootstrap container fix */
            .container { width: 100% !important; max-width: none !important; }
            /* Avoid breaking inside table rows if possible */
            tr { break-inside: avoid; page-break-inside: avoid; }
            /* CSS Paged Media support for label printing */
            @page { 
                -weasy-print: yes; 
                size: auto; 
                margin: 0; 
            }
            /* Force proper page breaks */
            .force-page-break { 
                break-after: page !important; 
                page-break-after: always !important; 
                clear: both !important;
                height: 0 !important;
                display: block !important;
            }
        """

    full_html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    /* Base reset */
                    html, body {{ width: 100%; margin: 0; padding: 0; }}
                    {margin_style}
                    {compatibility_css}
                </style>
            </head>
            <body class="container">
                {html_str}
            </body>
        </html>
        """

    try:
        # 6. Render with WeasyPrint
        doc = HTML(string=full_html, base_url=base_url).render()
        docs.append(doc)
    except Exception as e:
        _logger.error("WeasyPrint rendering failed: %s", e, exc_info=True)
        raise UserError(
            _("WeasyPrint rendering failed. Check server logs for details.\nError: %s")
            % str(e)
        )

    if not docs:
        return b""

    # 7. Merge Documents (if multiple, though we usually have one)
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
    """
        Override the default wkhtmltopdf runner to use WeasyPrint.
        """
    if not weasyprint:
        _logger.warning(
            "WeasyPrint not found, falling back to original wkhtmltopdf execution."
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

    _logger.info("Generating PDF with WeasyPrint for report: %s", report_ref)

    # 1. Resolve Base URL for assets
    # In Docker, localhost refers to the container. Odoo usually listens on 8069.
    # We prefer the frozen web.base.url, but ensure it's reachable.
    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
    if not base_url:
        base_url = "http://127.0.0.1:8069"

    docs = []

    # 2. Parse Margins from specific_paperformat_args
    # Odoo passes these as dictionary for wkhtmltopdf flags, e.g. {'--margin-top': 40}
    margin_style = ""
    if specific_paperformat_args:
        # Helper to safely get int/float from args
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

        # Extract explicit page size if present (for 'custom' formats)
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

        # Handle Page Size
        # Priority: Explicit dimensions > Landscape flag > Default (A4 usually)
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

        if margin_style:
            css_rules.append(margin_style)

        # 4. Handle Header/Footer with CSS Paged Media
        # We inject the HTML content into running elements
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

        # 5. Bootstrap/Odoo Compatibility Fixes for WeasyPrint
        # WeasyPrint handles flexbox reasonably well, but some Odoo reports
        # rely on webkit-specific behavior or specific Bootstrap versions.
        # Adding some generic fixes can help stability.
        compatibility_css = """
                /* Ensure background colors print */
                * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
                /* Bootstrap container fix */
                .container { width: 100% !important; max-width: none !important; }
                /* Avoid breaking inside table rows if possible */
                tr { break-inside: avoid; page-break-inside: avoid; }
                /* CSS Paged Media support for label printing */
                @page { 
                    -weasy-print: yes; 
                    size: auto; 
                    margin: 0; 
                }
                /* Force proper page breaks */
                .page-break-after-10-rows { 
                    break-after: page !important; 
                    page-break-after: always !important; 
                    clear: both !important;
                    height: 0 !important;
                    display: block !important;
                }
            """
        css_rules.append(compatibility_css)

        html_parts.append(body_str)

        full_html = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        /* Base reset */
                        html, body {{ width: 100%; margin: 0; padding: 0; }}
                        {chr(10).join(css_rules)}
                    </style>
                </head>
                <body class="container">
                    {"".join(html_parts)}
                </body>
            </html>
            """

        try:
            # 6. Render
            doc = HTML(string=full_html, base_url=base_url).render()
            docs.append(doc)
        except Exception as e:
            _logger.error("WeasyPrint rendering failed: %s", e, exc_info=True)
            raise UserError(
                _(
                    "WeasyPrint rendering failed. Check server logs for details.\nError: %s"
                )
                % str(e)
            )

    if not docs:
        return b""

    # 7. Merge Documents
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
