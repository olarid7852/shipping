from odoo import models, fields, api

class MyPicking(models.Model):
    _inherit = "stock.picking"
    shipment_item_id = fields.Many2one(
        string="Shipment Item",
        comodel_name="shipping.shipping_item",
        ondelete="cascade",
        readonly=True
    )
    shipping_id = fields.Char(related='shipment_item_id.shipping_id')

    def get_shipping_item(self):
        return self.env['shipping.shipping_item'].search(
            [('id', '=', self.shipment_item_id.id)])

    def set_shipping_item_to_collected(self):
        shipping_item = self.get_shipping_item()
        shipping_item.collected()

    # @api.onchange('state')
    # def onchange_state(self):
    #     pass
    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

            Normally that happens when the button "Done" is pressed on a Picking view.
            @return: True
        """
        self._check_company()
        todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in [
            'draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        # Check if there are ops not linked to moves yet
        for pick in self:
            if pick.owner_id:
                pick.move_lines.write(
                        {'restrict_partner_id': pick.owner_id.id})
                pick.move_line_ids.write({'owner_id': pick.owner_id.id})

                # # Explode manually added packages
                # for ops in pick.move_line_ids.filtered(lambda x: not x.move_id and not x.product_id):
                #     for quant in ops.package_id.quant_ids: #Or use get_content for multiple levels
                #         self.move_line_ids.create({'product_id': quant.product_id.id,
                #                                    'package_id': quant.package_id.id,
                #                                    'result_package_id': ops.result_package_id,
                #                                    'lot_id': quant.lot_id.id,
                #                                    'owner_id': quant.owner_id.id,
                #                                    'product_uom_id': quant.product_id.uom_id.id,
                #                                    'product_qty': quant.qty,
                #                                    'qty_done': quant.qty,
                #                                    'location_id': quant.location_id.id, # Could be ops too
                #                                    'location_dest_id': ops.location_dest_id.id,
                #                                    'picking_id': pick.id
                #                                    }) # Might change first element
                # # Link existing moves or add moves when no one is related
                for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                    # Search move with this product
                    moves = pick.move_lines.filtered(
                        lambda x: x.product_id == ops.product_id)
                    moves = sorted(moves, key=lambda m: m.quantity_done <
                                m.product_qty, reverse=True)
                    if moves:
                        ops.move_id = moves[0].id
                    else:
                        new_move = self.env['stock.move'].create({
                            'name': _('New Move:') + ops.product_id.display_name,
                            'product_id': ops.product_id.id,
                            'product_uom_qty': ops.qty_done,
                            'product_uom': ops.product_uom_id.id,
                                                        'description_picking': ops.description_picking,
                                                        'location_id': pick.location_id.id,
                                                        'location_dest_id': pick.location_dest_id.id,
                                                        'picking_id': pick.id,
                                                        'picking_type_id': pick.picking_type_id.id,
                                                        'restrict_partner_id': pick.owner_id.id,
                                                        'company_id': pick.company_id.id,
                        })
                        ops.move_id = new_move.id
                        new_move._action_confirm()
                        todo_moves |= new_move
                        #'qty_done': ops.qty_done})
        todo_moves._action_done(
            cancel_backorder=self.env.context.get('cancel_backorder'))
        self.write({'date_done': fields.Datetime.now()})
        self._send_confirmation_email()
        if self.picking_type_id.id == 1:
            shipping_item = self.get_shipping_item()
            shipping_item.set_arrived()
            
        elif self.picking_type_id.id == 2:
            self.set_shipping_item_to_collected()
        return True

class MyInvoice(models.Model):
    _inherit = "account.move"
    shipment_item_id = fields.Many2one(
        string="Shipment Item",
        comodel_name="shipping.shipping_item",
        ondelete="cascade",
        readonly=True
    )
    shipping_id = fields.Char(related='shipment_item_id.shipping_id')

    def check_for_availability_of_good(self):
        good = self.env['shipping.shipping_item'].search(
            [('payment_id', '=', self.id)])
        return good

    def set_reciept_to_ready(self, shipping_item):
        reciept = self.env['stock.picking'].search(
            [('shipment_item_id', '=', shipping_item.id)])
        reciept.action_assign()


    def _compute_amount(self):
        invoice_ids = [move.id for move in self if move.id and move.is_invoice(
            include_receipts=True)]
        self.env['account.payment'].flush(['state'])
        if invoice_ids:
            self._cr.execute(
                '''
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                        OR
                        (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                ''', [tuple(invoice_ids)]
            )
            in_payment_set = set(res[0] for res in self._cr.fetchall())
        else:
            in_payment_set = {}

        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * \
                (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * \
                (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * \
                (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * \
                (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies.pop(
            ) or move.company_id.currency_id
            is_paid = currency and currency.is_zero(
                move.amount_residual) or not move.amount_residual

            # Compute 'invoice_payment_state'.
            if move.state == 'posted' and is_paid:
                if move.id in in_payment_set:
                    move.invoice_payment_state = 'in_payment'
                else:
                    move.invoice_payment_state = 'paid'
            else:
                move.invoice_payment_state = 'not_paid'
            from datetime import datetime
            # import pudb; pudb.set_trace()
            # print('-'*50, '\n' * 10)
            # print(datetime.now())
            # print(move.invoice_payment_state)
            # print(move.state)
            # print(move)
            # print('\n' * 10, '+'*50)
            
            if move.invoice_payment_state == 'paid':
                shipping_item = move.check_for_availability_of_good()
                shipping_item.set_status_to_paid()
                if shipping_item:
                    move.set_reciept_to_ready(shipping_item)
