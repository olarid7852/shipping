from odoo import models, fields
class LibraryBook(models.Model):
    _name = 'library.ship_cargo'
    date = fields.Date('Departure Date', required=True)
    remark = fields.Char('Remark')
    items = fields.One2many('library.ship_cargo_item',
                            'cargo_id', string='items')
