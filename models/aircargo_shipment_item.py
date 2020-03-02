from odoo import models, fields, api


class ShippingItem(models.Model):
    _name = 'shipping.shipping_item'

    # common_fields
    shipping_id = fields.Char('ID', required=True)
    pkgs = fields.Float('Pkgs', required=True)
    wkg = fields.Float('W.kg', required=True)
    products = fields.Many2one(
        'product.product', string="Product", ondelete="cascade")
    marks = fields.Char('Marks')
    consignee_id = fields.Many2one(
        'res.partner',
        string="Consignee",
        ondelete="cascade",
        required=True
    )
    shipper_id = fields.Many2one(
        'res.partner',
        string='Shipper',
        ondelete="cascade",
        required=True
    )
    payment_id = fields.Many2one(
        'account.move',
        string="payment",
        ondelete="cascade",
        readonly=True
    )
    cargo_id = fields.Many2one(
        'shipping.cargo',
        string="Cargo",
        ondelete="cascade",
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('arrived', 'Arrived'),
        ('paid', 'Paid'),
        ('collected', 'Collected'),
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, track_visibility='always')
    customer_order = fields.Many2one(
        'stock.picking',
        string="Order",
        ondelete="cascade",
        readonly=True
    )
    # shipping_type = fields.Selection([
    #         ('ship', 'Ship'),
    #         ('air', 'Air'),
    #     ], required=True
    # )

    shipping_type = fields.Selection(related='cargo_id.shipping_type')
    reciept = fields.Many2one(
        'stock.picking',
        string="Reciept",
        ondelete="cascade",
        readonly=True
    )
    remark = fields.Char('Remarks')

    #Shipping only fields
    total_cbm = fields.Char('Total CBM')
    dest_port = fields.Char('Dest. Port')
    hbl = fields.Char(compute='_get_hbl', store=False)

    # Aircargo only fields
    vol = fields.Float('Vol.kg')
    quantity = fields.Integer('Quantity')
    sign = fields.Char('Sign')
    location = fields.Char('Location')
    hawb_no = fields.Char(compute='_get_hawb_no', store=False)

    @api.depends('shipping_id',)
    def _get_hawb_no(self):
        for rule in self:
            rule.hawb_no = self.shipping_id
            # rule.hbl = self.shipping_id

    @api.depends('shipping_id',)
    def _get_hbl(self):
        for rule in self:
            rule.hbl = self.shipping_id
            # rule.hbl = self.shipping_id

    @api.model
    def create(self, vals):
        new_item = super(ShippingItem, self).create(vals)
        new_item.create_reciept_and_customer_order()
        return new_item

    def get_product(self):
      return self.env['product.product'].search([('id', '=', self.products)])

    def collected(self):
        self.write({'state': 'collected'})

    def set_status_to_paid(self):
        self.write({'state': 'paid'})

    def create_reciept_and_customer_order(self):
        quantity_done = self.quantity
        if not quantity_done:
            quantity_done = self.wkg
        data = {
            'is_locked': True,
            'immediate_transfer': True,
            'picking_type_id': 2,
            'location_id': 8,
            'location_dest_id': 5,
            # 'scheduled_date': '2020-02-25 11:13:28',
            'move_type': 'direct',
            'user_id': 1,
            'company_id': 1,
            'partner_id': self.consignee_id.id,
            'origin': False,
            'owner_id': False,
            'priority': False,
            'note': False,
            'message_attachment_count': 0,
            'shipment_item_id': self.id
        }
        picking = self.env['stock.picking'].create(data)
        product_data = {
            'company_id': 1,
            'state': 'draft',
            'picking_type_id': 2,
            'location_id': 8,
            'location_dest_id': 5,
            'additional': False,
            # 'date_expected': '2020-02-25 11:38:34',
            'name': self.hawb_no,
            'product_id': self.products.id,
            'description_picking': self.hawb_no,
            'quantity_done': quantity_done,
            'product_uom': 1,
            'picking_id': picking.id
        }
        self.env["stock.move"].create(product_data)
        self.write({'customer_order': picking.id})
        product_data['picking_type_id'] =  1
        data = {
            'is_locked': True,
            'immediate_transfer': True,
            'picking_type_id': 1,
            'location_id': 8,
            'location_dest_id': 5,
            # 'scheduled_date': '2020-02-25 11:13:28',
            'move_type': 'direct',
            'user_id': 1,
            'company_id': 1,
            'partner_id': self.consignee_id.id,
            'origin': False,
            'owner_id': False,
            'priority': False,
            'note': False,
            'message_attachment_count': 0,
            'shipment_item_id': self.id
        }
        picking = self.env['stock.picking'].create(data)
        product_data['picking_id'] = picking.id
        self.env["stock.move"].create(product_data)
        self.write({'reciept': picking.id})
        picking.action_assign()

    def set_arrived(self):
        return self.button_set_arival()

    def button_set_arival(self):
        self.payment_id.action_post()
        self.write({'state': 'arrived'})
        product_price_per_unit = 5
        product_price = product_price_per_unit * self.quantity
        quantity = self.quantity
        if not product_price:
            product_price = product_price_per_unit * self.wkg
            quantity = self.wkg
        tax_price = 0.15 * product_price
        total_price = product_price + tax_price
        # import pudb; pudb.set_trace()
        recievable_account = self.consignee_id.property_account_receivable_id
        payable_account = self.consignee_id.property_account_payable_id
        # if journal.default_credit_account_id:
        #     payable_account = journal.default_credit_account_id
        recievable_account_id = recievable_account.id
        payable_account_id = payable_account.id
        import pudb; pudb.set_trace()
        invoice_vals = {
            'type': 'out_invoice',
            'invoice_user_id': 1,
            'partner_id': self.consignee_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': self.products.name,
                'price_unit': product_price_per_unit,
                'quantity': quantity,
                'product_id': self.products.id,
                'product_uom_id': False,
                'tax_ids': [(6, 0, [1])],
            })],
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.write({'payment_id': invoice.id})
        self.env.cr.commit()