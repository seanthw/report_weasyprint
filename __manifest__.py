{
    'name': 'WeasyPrint Report Engine',
    'version': '1.0',
    'category': 'Reporting',
    'summary': 'Replaces wkhtmltopdf with WeasyPrint for PDF generation',
    'description': """
        This module overrides the standard Odoo PDF generation (which uses wkhtmltopdf)
        to use WeasyPrint instead. This allows for better support of modern CSS features
        and avoids the dependency on the unmaintained wkhtmltopdf.
    """,
    'depends': ['base', 'web'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
