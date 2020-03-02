from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # default_seats = fields.Integer(string='My Setting')
    my_setting = fields.Char(string='My Setting')
    sale_account = fields.Many2one(
        "account.account",
        string="Sale account journal",
        ondelete="cascade",
        default=0
    )
    tax_account = fields.Many2one(
        "account.account",
        string="Tax account journal",
        ondelete="cascade",
        default=0
    )
    general_account = fields.Many2one(
        "account.account",
        string="General account journal",
        ondelete="cascade",
        default=0
    )

    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     res.update(
    #         my_setting=self.env['ir.config_parameter'].sudo().get_param('library.my_setting')
    #     )
    #     return res

    @api.model
    def set_values(self):
        import pudb
        pudb.set_trace()
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'library.my_setting', self.my_setting)
        self.env['ir.config_parameter'].sudo().set_param(
            'library.sale_account', self.sale_account)
        self.env['ir.config_parameter'].sudo().set_param(
            'library.tax_account', self.tax_account)
        self.env['ir.config_parameter'].sudo().set_param(
            'library.general_account', self.general_account)

    @api.model
    def get_values(self):
        # import pudb; pudb.set_trace()
        res = super(ResConfigSettings, self).get_values()
        res.update(
            my_setting=self.env['ir.config_parameter'].sudo().get_param(
                'library.my_setting'),
            sale_account=self.env['ir.config_parameter'].sudo().get_param(
                'library.sale_account'),
            tax_account=self.env['ir.config_parameter'].sudo().get_param(
                'library.tax_account'),
            general_account=self.env['ir.config_parameter'].sudo().get_param(
                'library.general_account'),
        )
        return res
