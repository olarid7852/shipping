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
        new_item = super(LibraryBook, self).create(vals)
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
        create_method = self.env['account.move'].create
        data = {'user_id': 1,
                'type': 'out_invoice', 'journal_id': 1, 'partner_id': self.consignee_id.id, 'shipment_item_id': self.id}
        # import pudb
        # pudb.set_trace()
        journal = self.env['account.journal'].search(
            [('id', '=', 1)])
        invoice_id = create_method(data)
        # self.create_reciept_and_customer_order()
        create_method = self.env['account.move.line'].create
        product_price_per_unit = 5
        product_price = product_price_per_unit * self.quantity
        if not product_price:
            product_price = product_price_per_unit * self.wkg
        tax_price = 0.15 * product_price
        total_price = product_price + tax_price
        # import pudb; pudb.set_trace()
        recievable_account = self.consignee_id.property_account_receivable_id
        payable_account = self.consignee_id.property_account_payable_id
        
        if journal.default_debit_account_id:
            recievable_account = journal.default_debit_account_id
        if journal.default_credit_account_id:
            payable_account = journal.default_credit_account_id
        recievable_account_id = recievable_account.id
        payable_account_id = payable_account.id
        line_1 = {
            'account_id': recievable_account_id,
            # 'sequence': 10,
            'name': False,
            'quantity': 1,
            'price_unit': -1 * total_price,
            'discount': 0,
            'debit': total_price,
            'credit': 0,
            'amount_currency': 0,
            'date_maturity': '2020-02-24',
            'currency_id': False,
            'partner_id': False,
            'product_uom_id': False,
            'product_id': False,
            'payment_id': False,
            'tax_ids': [[6, False, []]],
            'tax_base_amount': 0,
            'tax_exigible': True,
            'tax_repartition_line_id': False,
            'tag_ids': [[6, False, []]],
            'analytic_account_id': False,
            'analytic_tag_ids': [[6, False, []]],
            'recompute_tax_line': False,
            'display_type': False,
            'is_rounding_line': False,
            'exclude_from_invoice_tab': True,
            'move_id': invoice_id.id}
        line_2 = {'account_id': payable_account_id,
                #   'sequence': 10,
                  'name': 'Tax 15.00%',
                  'quantity': 1,
                  'price_unit': tax_price,
                  'discount': 0,
                  'debit': 0,
                  'credit': tax_price,
                  'amount_currency': 0,
                  'date_maturity': False,
                  'currency_id': False,
                  'partner_id': False,
                  'product_uom_id': False,
                  'product_id': False,
                  'payment_id': False,
                  'tax_ids': [[6, False, []]],
                  'tax_base_amount': 102,
                  'tax_exigible': True,
                  'tax_repartition_line_id': 2,
                  'tag_ids': [[6, False, []]],
                  'analytic_account_id': False,
                  'analytic_tag_ids': [[6, False, []]],
                  'recompute_tax_line': False,
                  'display_type': False,
                  'is_rounding_line': False,
                  'exclude_from_invoice_tab': True,
                  'move_id': invoice_id.id}
        line_3 = {'account_id': payable_account_id,
                #   'sequence': 10,
                  'name': 'Cake mold',
                  'quantity': self.quantity,
                  'price_unit': product_price_per_unit,
                  'discount': 0,
                  'debit': 0,
                  'credit': product_price,
                  'amount_currency': 0,
                  'date_maturity': False,
                  'currency_id': False,
                  'partner_id': False,
                  'product_uom_id': 1,
                  'product_id': self.products.id,
                  'payment_id': False,
                  'tax_ids': [[6, False, [1]]],
                  'tax_base_amount': 0,
                  'tax_exigible': True,
                  'tax_repartition_line_id': False,
                  'tag_ids': [[6, False, []]],
                  'analytic_account_id': False,
                  'analytic_tag_ids': [[6, False, []]],
                  'recompute_tax_line': False,
                  'display_type': False,
                  'is_rounding_line': False,
                  'exclude_from_invoice_tab': False,
                  'move_id': invoice_id.id}
        data = [line_1, line_2, line_3]
        create_method(data)
        # {
        #     "name": self.hawb_no,
        #     "price_unit": 88,
        #     "product_uom_id": 1,
        #     "quantity": 2,
        #     "account_id": 33,
        #     "product_id": self.products.id})]
        # }
# 'user_id': self.cosignee_id, 'name': self.hawb_no, 'invoice_vendor_bill_id': invoice_id, 'price_unit': 10})
        # journal_id = self.env['account.move.line'].create(
        #     {'move_id': invoice_id.id, 'name': 'Main', 'quantity': 1, 'price_unit': self.wkg * 4, 'account_id': 33})
        # invoice_line=self.env['account.move.line'].create(
        #                                              {'name': self.hawb_no,
        # 'move_id': invoice_id.id,
        # 'partner_id': self.cosignee_id.id,
        # 'company_id': self.cosignee_id.id,
        # 'product_id': self.products.id,
        # 'quantity': 1.0,
        # 'date_maturity': False,
        # 'price_unit': 12,
        # 'account_id': 33
        # })
        print(invoice_id)
        self.write({'payment_id': invoice_id})
        self.env.cr.commit()
