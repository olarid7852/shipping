from odoo import models, fields, api
import xlrd
import base64
from datetime import datetime
from ..misc import aircargo_sheets


class ShippingCargo(models.Model):
    _name = 'shipping.cargo'

    # general_fields
    data_file = fields.Binary('File')
    shipping_id = fields.Char("ID")
    shipping_type = fields.Selection([
        ('ship', 'Ship'),
        ('air', 'Air'),
    ], required=True, string="Shipping Type")
    departure_date = fields.Date('Departure Date')
    items = fields.One2many('shipping.shipping_item',
                            'cargo_id', string='items')
    ship_items = fields.One2many('shipping.shipping_item',
                                 'cargo_id', string='items')
    general_items = fields.One2many('shipping.shipping_item',
                                 'cargo_id', string='items')

    # aircargo fields
    # mawb_no = fields.Char('MAWB NO')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('arrived', 'Arrived'),
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, track_visibility='always')
    discharge_port = fields.Char('Port of discharge')
    arrival_date = fields.Date('Arrival Date')
    flt_no = fields.Char('Fleet No')
    consign_to = fields.Char('Consign to')
    shipped_by = fields.Many2one('res.partner', ondelete="cascade")
    mawb_no = fields.Char(compute='_get_mawb', store=True)

    # shipping fields
    remark = fields.Char('Remark')
    groupage = fields.Char('Groupage')

    @api.depends('shipping_id',)
    def _get_mawb(self):
        for rule in self:
            rule.mawb_no = self.shipping_id
    

    def import_file(self):
        if self.shipping_type == 'air':
            return self.import_file_for_aircargo()
        else:
            return self.import_file_for_shipfreight()
    def clean_dic(self, data):
        for key in data.keys():
            if data[key] == '':
                # import pudb; pudb.set_trace()
                data[key] = False
        return data
    def import_file_for_aircargo(self):
        # import pudb; pudb.set_trace()
        book = xlrd.open_workbook(
            file_contents=base64.decodestring(self.data_file))
        sheet = book.sheet_by_index(0)
        shipment_data = aircargo_sheets.populate_shipment_data(
            self.shipping_type, sheet)
        shipment_data = self.clean_dic(shipment_data)
        self.write(shipment_data)
        cargo = self
        aircargo_items_data = aircargo_sheets.populate_shipping_items_data(self.shipping_type, sheet)
        for item_data in aircargo_items_data:
            new_item_data = {}
            same_fields = ['pkgs', 'wkg', 'marks', ]
            new_item_data['shipping_id'] = item_data['hawb_no']
            new_item_data['payment_choice'] = float(
                item_data['payment'].split(' ')[-1])
            new_item_data['payment_company'] = float(item_data['payment'].split(' ')[-1])
            product_name = item_data['commodity']
            product = self.env['product.product'].search([('name', '=', product_name)])
            if not product:
                new_item_data['products'] = self.env['product.product'].create({
                    'name': product_name
                }).id
            else:
                new_item_data['products'] = product.id
            consignee_data = item_data['name']
            consignee = self.find_or_create_partner(
                self.shipping_type, consignee_data)
            new_item_data['consignee_id'] = consignee.id

            shipper_data = item_data['shipper']
            shipper = self.find_or_create_partner(
                self.shipping_type, shipper_data)
            new_item_data['shipper_id'] = shipper.id
            new_item_data['cargo_id'] = cargo.id
            for field in same_fields:
                new_item_data[field] = item_data[field]
            new_item_data = self.clean_dic(new_item_data)
            self.env['shipping.shipping_item'].create(new_item_data)
        return True

    def find_or_create_partner(self, shipping_type, partner_string):
        if shipping_type == 'air':
            partner_name = partner_string.split("\n")[0]
            partner_phone_no = partner_string.split("\n")[1]
        else:
            name_and_phone_number_seperation_index = partner_string.find(" ")
            partner_name = partner_string[:name_and_phone_number_seperation_index]
            partner_phone_no = partner_string[name_and_phone_number_seperation_index:]
        partner = self.env['res.partner'].search(
            [('name', '=', partner_name)])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': partner_name,
                'phone': partner_name
            })
            shipper = self.env['res.company'].create({
                'name': partner_name,
                'partner_id': partner.id
            })
        return partner

    def import_file_for_shipfreight(self):
        book = xlrd.open_workbook(
            file_contents=base64.decodestring(self.data_file))
        sheet = book.sheet_by_index(0)
        shipment_data = aircargo_sheets.populate_shipment_data(
            self.shipping_type, sheet)
        # import pudb; pudb.set_trace()
        shipment_data['shipping_type'] = 'ship'
        # cargo = self.env['shipping.cargo'].create(shipment_data)
        shipment_data = self.clean_dic(shipment_data)
        self.write(shipment_data)
        cargo = self
        aircargo_items_data = aircargo_sheets.populate_shipping_items_data(self.shipping_type,
            sheet)
        for item_data in aircargo_items_data:
            new_item_data = {}
            same_fields = ['pkgs', 'wkg', 'marks',
                           'dest_port', 'shipping_order']
            new_item_data['shipping_id'] = item_data['hbl']
            new_item_data['payment_choice'] = float(item_data['payment'])
            new_item_data['payment_company'] = float(item_data['payment'])
            product_name = item_data['goods_description']
            product = self.env['product.product'].search(
                [('name', '=', product_name)])
            if not product:
                new_item_data['products'] = self.env['product.product'].create({
                    'name': product_name
                }).id
            else:
                new_item_data['products'] = product.id
            consignee_data = item_data['consignee']
            consignee = self.find_or_create_partner(self.shipping_type, consignee_data)
            new_item_data['consignee_id'] = consignee.id

            shipper_data = item_data['shipper']
            shipper = self.find_or_create_partner(
                self.shipping_type, shipper_data)
            new_item_data['shipper_id'] = shipper.id
            new_item_data['cargo_id'] = cargo.id
            for field in same_fields:
                new_item_data[field] = item_data[field]
            new_item_data = self.clean_dic(new_item_data)
            self.env['shipping.shipping_item'].create(new_item_data)
        return True

    def action_set_arival(self):
        # import pudb; pudb.set_trace()
        # import pudb; pudb.set_trace()
        for shipping_item in list(self.ship_items):
            shipping_item.button_set_arival()
        self.write({'state': 'arrived'})
