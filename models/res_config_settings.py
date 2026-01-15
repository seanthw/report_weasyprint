from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    weasyprint_enabled = fields.Boolean(
        string="Enable WeasyPrint globally",
        help="Enable WeasyPrint for all PDF reports. If disabled, reports will use wkhtmltopdf by default.",
        default=False,
    )

    weasyprint_allowed_modules = fields.Many2many(
        "ir.module.module",
        string="Allowed modules",
        domain=[("state", "=", "installed")],
        help="If WeasyPrint is globally disabled, these specific modules will still use WeasyPrint for their reports.",
    )

    weasyprint_blocked_modules = fields.Many2many(
        "ir.module.module",
        relation="config_weasyprint_blocked_modules",
        column1="config_id",
        column2="module_id",
        string="Blocked modules",
        domain=[("state", "=", "installed")],
        help="If WeasyPrint is globally enabled, these specific modules will NOT use WeasyPrint for their reports.",
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "report_weasyprint.enabled", self.weasyprint_enabled
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "report_weasyprint.allowed_modules",
            ",".join(self.weasyprint_allowed_modules.mapped("name")),
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "report_weasyprint.blocked_modules",
            ",".join(self.weasyprint_blocked_modules.mapped("name")),
        )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env["ir.config_parameter"].sudo()

        enabled = ICP.get_param("report_weasyprint.enabled", False)
        allowed_names = (
            ICP.get_param("report_weasyprint.allowed_modules", "").split(",")
            if ICP.get_param("report_weasyprint.allowed_modules")
            else []
        )
        blocked_names = (
            ICP.get_param("report_weasyprint.blocked_modules", "").split(",")
            if ICP.get_param("report_weasyprint.blocked_modules")
            else []
        )

        allowed_modules = self.env["ir.module.module"].search(
            [("name", "in", allowed_names)]
        )
        blocked_modules = self.env["ir.module.module"].search(
            [("name", "in", blocked_names)]
        )

        res.update(
            {
                "weasyprint_enabled": enabled,
                "weasyprint_allowed_modules": [(6, 0, allowed_modules.ids)],
                "weasyprint_blocked_modules": [(6, 0, blocked_modules.ids)],
            }
        )
        return res
