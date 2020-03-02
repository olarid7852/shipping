from odoo import models, fields, api
class ShippingCargo(models.Model):
    _name = 'shipping.cargo'

    #general_fields
    shipping_id = fields.Char("ID")
    shipping_type = fields.Selection([
        ('ship', 'Ship'),
        ('air', 'Air'),
    ], required=True, string="Shipping Type")
    departure_date = fields.Date('Departure Date', required=True)
    items = fields.One2many('shipping.shipping_item',
                            'cargo_id', string='items')
    ship_items = fields.One2many('shipping.shipping_item',
                            'cargo_id', string='items')

    #aircargo fields
    # mawb_no = fields.Char('MAWB NO')
    dischare_port = fields.Char('Port of discharge')
    arrival_date = fields.Date('Arrival Date')
    flt_no = fields.Char('Fleet No')
    consign_to = fields.Char('Consign to')
    shipped_by = fields.Many2one('res.partner', ondelete="cascade")
    mawb_no = fields.Char(compute='_get_mawb', store=True)

    #shipping fields
    remark = fields.Char('Remark')

    @api.depends('shipping_id',)
    def _get_mawb(self):
        for rule in self:
            rule.mawb_no = self.shipping_id
