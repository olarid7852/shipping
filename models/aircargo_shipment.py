from odoo import models, fields
class LibraryBook(models.Model):
    _name = 'library.aircargo'
    mawb_no = fields.Char('MAWB NO', required=True)
    dischare_port = fields.Char('Port of discharge', required=True)
    arrival_date = fields.Date('Arrival Date', required=True)
    departure_date = fields.Date('Departure Date', required=True)
    flt_no = fields.Char('Fleet No', required=True)
    consign_to = fields.Char('Consign to', required=True)
    shipped_by = fields.Many2one('res.partner', required=True)
    items = fields.One2many('library.aircargo_item', 'cargo_id', string='items')