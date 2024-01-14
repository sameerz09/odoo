from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_data = [{'id': account.id, 'name': account.name} for account in accounts]

        return account_data

    @api.model
    def get_analytic_accounts(self):
        accounts = self.env['account.analytic.account'].search([])

        account_data = [{'id': account.id, 'name': account.name} for account in accounts]

        return account_data

    @api.model
    def get_all_partners(self):
        partners = self.env['res.partner'].search([])

        partner_data = [{'id': partner.id, 'name': partner.name} for partner in partners]

        return partner_data

    @api.model
    def get_balance(self, account_id, end_date):
        # Define search criteria to filter account move lines
        domain = [('account_id', '=', account_id),
                  ('date', '<=', end_date)]

        # Retrieve the most recent account move line based on the criteria
        move_line = self.env['account.move.line'].search(domain, order='date DESC', limit=1)

        # Prepare ledger data or return an empty list if no move lines are found
        balance_info = [{
            'name': move_line.name,
            'date': move_line.date,
            'balance': move_line.balance,
        }] if move_line else []

        # Return the general ledger data
        return {'balance_info': balance_info}

    @api.model
    def general_ledger_report(self, account_id, start_date, end_date):
        domain = [
            ('account_id', '=', account_id),
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ]
        move_lines = self.env['account.move.line'].search(domain)

        ledger_data = []

        for line in move_lines:
            analytic_info = self.env['account.analytic.line'].search([('move_line_id', '=', line.id)], limit=1)
            analytic_partner_id = analytic_info.partner_id if analytic_info else False
            partner_name = analytic_partner_id.name if analytic_info else False
            analytic_account_id = analytic_info.account_id if analytic_info else ""
            analytic_account_name = analytic_account_id.name if analytic_info else ""
            analytic_account_amount = analytic_info.amount if analytic_info else "",
            partner_id = line.partner_id.id if line.partner_id else ""
            partner_type = None
            if line.partner_id:
                partner = line.partner_id
                if partner.customer_rank > 0 and partner.supplier_rank > 0:
                    partner_type = 'Customer/Vendor'
                elif partner.customer_rank > 0:
                    partner_type = 'Customer'
                elif partner.supplier_rank > 0:
                    partner_type = 'Vendor'

            else:
                partner_type = ""

            ledger_data.append({
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'account_root_id': line.account_root_id.id,
                'analytic_move_id': analytic_info.id,
                'analytic_account_amount': analytic_account_amount,
                'analytic_account_name': analytic_account_name,
                'partner_id': line.partner_id.name,
                'partner_type': partner_type,

            })

        return {
            'ledger_data': ledger_data,
        }

    ##create/get/delete_bills
    @api.model
    def create_bill(self, bill_vals, partner_id, bill_date, bill_date_due, reference, narration):
        """
        Create a bill and corresponding analytic lines based on the provided data.
        """
        # Prepare the invoice lines
        bill_lines = []
        for line in bill_vals:
            bill_line_vals = {
                'name': line.get('description', ''),
                'quantity': line.get('quantity', 1.0),
                'price_unit': line.get('price_unit', 0.0),
                'account_id': line.get('account_id'),
                'product_id': line.get('product_id', False),
            }
            bill_lines.append((0, 0, bill_line_vals))

        # Create a new AR invoice record
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id,
            'invoice_date': bill_date,
            'invoice_date_due': bill_date_due,
            'ref': self.name,
            'narration': narration,
            'invoice_line_ids': bill_lines,
        })
        bill.action_post()

        # Create analytic lines for each invoice line if analytic_account_id is provided
        for line, line_vals in zip(bill.invoice_line_ids, bill_lines):
            analytic_account_id = line_vals.get('analytic_account_id')
            if analytic_account_id:
                self.env['account.analytic.line'].create({
                    # 'account_id': analytic_account_id,
                    'account_id': 1,
                    'name': line.name,
                    'amount': line.price_subtotal,  # or any other relevant amount
                    # 'move_id': line.id,
                    # Add other necessary fields
                })

        return f"ID: {bill.id}, Name: {bill.name}, Amount: {bill.amount_total}, Date: {bill.invoice_date}, Due Date: {bill.invoice_date_due}"

    @api.model
    def get_bill(self, bill_id):
        # Define search criteria to filter bills
        domain = [
            ('id', '=', bill_id),
            ('move_type', '=', 'in_invoice'),
        ]

        # Retrieve bills based on the criteria
        bill = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        bill_data = []

        # for bill in bills:
        # Retrieve invoice lines for each bill
        bill_lines = bill.invoice_line_ids
        selected_account_id = (
                bill_lines and bill_lines[0].account_id.name or False
        )

        # Assemble bill data
        bill_data.append({
            'id': bill.id,
            'bill_number': bill.id,
            'bill_date': bill.invoice_date,
            'supplier_id': bill.partner_id.name,
            'amount': bill.amount_total,
            'state': bill.payment_state,
            'selected_account_id': selected_account_id,
            # Add more bill details here as needed
        })

        # Create a dictionary with a "bill_info" key
        response = {'invoice_info': bill_data}

        return response

    @api.model
    def delete_bill(self, bill_id):
        Bill = self.env['account.move']
        # bill = Bill.search([('id', '=', bill_id), ('move_type', '=', 'in_invoice')])
        bill = Bill.search([('id', '=', bill_id)])

        if not bill:
            return "Bill not found."

        # Check if the bill is posted (validated)
        if bill.state == 'posted':
            # Add logic to cancel related journal entries (if any)
            # Example: bill.button_draft() or bill.button_cancel()
            try:
                bill.button_draft()  # Reset to draft
            except Exception as e:
                return "Failed to reset bill to draft: {}".format(e)

        # Additional logic to unreconcile payments if the bill is reconciled

        try:
            bill.unlink()  # Delete the bill
            return "Bill deleted successfully."
        except Exception as e:
            return "Failed to delete bill: {}".format(e)

    @api.model
    def create_bill_payment(self, bill_vals, partner_id, bill_date, bill_date_due, ref, narration,
                            payment_method_id, journal_id):
        """
        Create a bill payment based on the provided data.

        :param bill_vals: List of dictionaries containing line data for the payment.
        :param partner_id: Partner ID for the payment.
        :param bill_date: Bill date for the payment.
        :param bill_date_due: Due date for the payment.
        :param ref: Reference for the payment.
        :param narration: Narration for the payment.
        :param payment_method_id: ID of the payment method used for the payment.
        :param journal_id: ID of the journal to record the payment.
        :return: The created payment record.
        """
        # Create a new payment record
        payment = self.env['account.payment'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id,
            'payment_type': 'outbound',  # For bill payment, it's typically 'outbound'
            'payment_method_id': payment_method_id,
            'journal_id': journal_id,
            'payment_date': bill_date,  # Set payment date as the invoice date or adjust as needed
            'communication': ref,  # Communication can be used as reference
            'invoice_ids': [(0, 0, bill_vals)],
            'invoice_date': bill_date,
            'invoice_date_due': bill_date_due,
            'ref': ref,
            'narration': narration,
        })

        return payment

    @api.model
    def delete_bill_payment(self, payment_id):
        invoice = self.env['account.move']
        payment = invoice.search([('id', '=', payment_id), ('move_type', '=', 'entry')])

        if not payment:
            return "Payment not found."

        # Check if the bill is posted (validated)
        if payment.state == 'posted':
            # Add logic to cancel related journal entries (if any)
            # Example: bill.button_draft() or bill.button_cancel()
            try:
                payment.button_draft()  # Reset to draft
            except Exception as e:
                return "Failed to reset Payment to draft: {}".format(e)

        # Additional logic to unreconcile payments if the Invoice is reconciled

        try:
            payment.unlink()  # Delete the bill
            return "Payment deleted successfully."
        except Exception as e:
            return "Failed to delete Payment: {}".format(e)




    #### create / get / delete_invoice_payment

    @api.model
    def get_invoice(self, invoice_id):
        """
        Retrieve a bill and its details based on the bill ID.
        :param bill_id: ID of the bill to retrieve.
        :return: A dictionary containing the bill data or an error message.
        """
        # Define search criteria to filter bills
        domain = [
            ('id', '=', invoice_id),
            ('move_type', '=', 'out_invoice'),
        ]

        # Retrieve the bill based on the criteria
        invoice = self.env['account.move'].search(domain, order='invoice_date', limit=1)
        if not invoice:
            return {'error': 'Bill not found'}

        # Prepare data for invoice lines
        invoice_line_data = [{
            'line_id': line.id,
            'account_id': line.account_id.id,
            'account_name': line.account_id.name,
            'quantity': line.quantity,
            'price_unit': line.price_unit,
        } for line in invoice.invoice_line_ids]

        # Assemble bill data
        invoice_data = {
            'id': invoice.id,
            'bill_number': invoice.ref,
            'bill_date': invoice.invoice_date,
            'supplier_id': invoice.partner_id.name,
            'amount': invoice.amount_total,
            'state': invoice.payment_state,
            'invoice_lines': invoice_line_data,
        }

        return {'invoice_info': invoice_data}

    @api.model
    def delete_bill(self, bill_id):
        Bill = self.env['account.move']
        bill = Bill.search([('id', '=', bill_id), ('move_type', '=', 'in_invoice')])

        if not bill:
            return "Bill not found."

        # Check if the bill is posted (validated)
        if bill.state == 'posted':
            # Add logic to cancel related journal entries (if any)
            # Example: bill.button_draft() or bill.button_cancel()
            try:
                bill.button_draft()  # Reset to draft
            except Exception as e:
                return "Failed to reset bill to draft: {}".format(e)

        # Additional logic to unreconcile payments if the bill is reconciled

        try:
            bill.unlink()  # Delete the bill
            return "Bill deleted successfully."
        except Exception as e:
            return "Failed to delete bill: {}".format(e)

    ##create/get/delete_bills payment


    @api.model
    def get_bill_payment(self, payment_id):
        # Define search criteria to filter bills
        domain = [
            ('id', '=', payment_id),
            ('move_type', '=', 'in_invoice'),
        ]

        # Retrieve bills based on the criteria
        payment = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        payment_data = []

        # for bill in bills:
        # Retrieve invoice lines for each bill
        payment_lines = payment.invoice_line_ids
        selected_account_id = (
                payment_lines and payment_lines[0].account_id.name or False
        )

        # Assemble bill data
        payment_data.append({
            'id': payment.id,
            'bill_number': payment.id,
            'bill_date': payment.invoice_date,
            'supplier_id': payment.partner_id.name,
            'amount': payment.amount_total,
            'state': payment.payment_state,
            'selected_account_id': selected_account_id,
            # Add more bill details here as needed
        })

        # Create a dictionary with a "bill_info" key
        response = {'payment_info': payment_data}

        return response

    @api.model
    def get_bill_payment_by_journal_entry_id(self, journal_entry_id):
        Payment = self.env['account.payment']
        # Search for payment associated with the given journal entry
        payment = Payment.search([('move_id', '=', journal_entry_id)], limit=1)

        if payment:
            # Prepare a dictionary of relevant payment details
            payment_data = {
                'id': payment.id,
                'name': payment.name,
                'amount': payment.amount,
                # 'payment_date': payment.payment_date,
                'partner_id': payment.partner_id.id,
                'partner_name': payment.partner_id.name,
                'state': payment.state,
                # Include other fields as necessary
            }
            return payment_data
        else:
            return {'error': "No payment found for the provided journal entry ID."}




    @api.model
    def create_ar_invoice_payment(self, invoice_id, journal_id, payment_date, payment_amount, payment_method_id):
        """
        This method processes a payment for an Accounts Receivable (AR) invoice.

        Args:
            invoice_id (int): The ID of the AR invoice to be paid.
            journal_id (int): The ID of the payment journal.
            payment_date (date): The date when the payment is made.
            payment_amount (float): The total amount of the payment.
            payment_method_id (int): The ID of the used payment method.

        Returns:
            dict: A dictionary containing either a success message and payment ID, or an error message.
        """
        # Fetching the specified AR invoice
        invoice = self.env['account.move'].browse(invoice_id)

        # Validation checks for the invoice
        if not invoice or invoice.move_type != 'out_invoice':
            return {'error': 'Invalid invoice: Not found or not a customer invoice.'}
        if invoice.state != 'posted':
            return {'error': 'Invoice processing error: Must be in "posted" state.'}
        payment_method_line = self.env['account.payment.method.line'].search(
            [('payment_method_id', '=', payment_method_id)], limit=1)
        if not payment_method_line:
            return {'error': 'Invalid payment method or payment method line not found.'}

        # Creating the payment record
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': payment_amount,
            'journal_id': journal_id,
            'payment_method_line_id': payment_method_line.id,
            'invoice_line_ids': [(6, 0, [invoice_id])],
        })

        # Validating the payment
        payment.action_post()
        return {'success': 'Payment successfully processed.', 'payment_id': payment.id}

    @api.model
    def create_bill_payment(self, invoice_id, journal_id, payment_date, payment_amount, payment_method_id):
        """
        This method processes a payment for an Accounts Receivable (AR) invoice.

        Args:
            invoice_id (int): The ID of the AR invoice to be paid.
            journal_id (int): The ID of the payment journal.
            payment_date (date): The date when the payment is made.
            payment_amount (float): The total amount of the payment.
            payment_method_id (int): The ID of the used payment method.

        Returns:
            dict: A dictionary containing either a success message and payment ID, or an error message.
        """
        # Fetching the specified AR invoice
        invoice = self.env['account.move'].browse(invoice_id)

        # Validation checks for the invoice
        if not invoice:
            return {'error': 'Invalid Bill: Not found  the Bill Number.'}
        if invoice.move_type != 'in_invoice':
            return {'error': 'the type not in_invoice'}

        if invoice.state != 'posted':
            return {'error': 'Invoice processing error: Must be in "posted" state.'}
        payment_method_line = self.env['account.payment.method.line'].search(
            [('payment_method_id', '=', payment_method_id)], limit=1)
        if not payment_method_line:
            return {'error': 'Invalid payment method or payment method line not found.'}

        # Creating the payment record
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'supplier',
            'partner_id': invoice.partner_id.id,
            'amount': payment_amount,
            'journal_id': journal_id,
            'payment_method_line_id': payment_method_line.id,
            'invoice_line_ids': [(6, 0, [invoice_id])],
        })

        # Validating the payment
        payment.action_post()
        return {'success': 'Payment successfully processed.', 'payment_id': payment.id}


    @api.model
    def get_invoice_payment(self, payment_id):
        # Define search criteria to filter bills
        domain = [
            ('id', '=', payment_id),
            ('move_type', '=', 'out_invoice'),
        ]

        # Retrieve bills based on the criteria
        payment = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        payment_data = []

        # for bill in bills:
        # Retrieve invoice lines for each bill
        payment_lines = payment.invoice_line_ids
        selected_account_id = (
                payment_lines and payment_lines[0].account_id.name or False
        )

        # Assemble bill data
        payment_data.append({
            'id': payment.id,
            'bill_number': payment.id,
            'bill_date': payment.invoice_date,
            'supplier_id': payment.partner_id.name,
            'amount': payment.amount_total,
            'state': payment.payment_state,
            'selected_account_id': selected_account_id,
            # Add more bill details here as needed
        })

        # Create a dictionary with a "bill_info" key
        response = {'payment_info': payment_data}

        return response

    @api.model
    def delete_ar_invoice(self, invoice_id):
        """
        Delete an AR invoice based on the provided invoice ID.
        :param invoice_id: ID of the invoice to delete.
        :return: A success message or an error message.
        """
        # Retrieve the AR invoice based on the ID
        invoice = self.env['account.move'].search([
            ('id', '=', invoice_id),
            ('move_type', '=', 'out_invoice')  # AR invoices have the move_type 'out_invoice'
        ], limit=1)

        if not invoice:
            return "AR invoice not found."

        # Check if the invoice is in the 'draft' or 'cancel' state
        if invoice.state not in ['draft', 'cancel']:
            return "Invoice must be in 'draft' or 'cancel' state to be deleted."

        try:
            invoice.unlink()  # Delete the invoice
            return "AR invoice deleted successfully."
        except Exception as e:
            return "Failed to delete AR invoice: {}".format(e)

    #####create/get/delete_invoice

    @api.model
    def create_ar_invoice(self, invoice_vals, partner_id, invoice_date, invoice_date_due, reference, narration):
        """
        Create an AR invoice and corresponding analytic lines based on the provided data.
        """
        # Prepare the invoice lines
        invoice_lines = []
        for line in invoice_vals:
            invoice_line_vals = {
                'name': line.get('description', ''),
                'quantity': line.get('quantity', 1.0),
                'price_unit': line.get('price_unit', 0.0),
                'account_id': line.get('account_id'),
                'product_id': line.get('product_id', False),
            }
            invoice_lines.append((0, 0, invoice_line_vals))

        # Create a new AR invoice record
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': invoice_date,
            'invoice_date_due': invoice_date_due,
            'ref': self.name,
            'narration': narration,
            'invoice_line_ids': invoice_lines,
        })
        invoice.action_post()

        # Create analytic lines for each invoice line if analytic_account_id is provided
        for line, line_vals in zip(invoice.invoice_line_ids, invoice_vals):
            analytic_account_id = line_vals.get('analytic_account_id')
            if analytic_account_id:
                self.env['account.analytic.line'].create({
                    'account_id': analytic_account_id,
                    'name': line.name,
                    'amount': line.price_subtotal,  # or any other relevant amount
                    # 'move_id': line.id,
                    # Add other necessary fields
                })

        return f"ID: {invoice.id}, Name: {invoice.name}, Amount: {invoice.amount_total}, Date: {invoice.invoice_date}, Due Date: {invoice.invoice_date_due}"

    @api.model
    def get_ar_invoice(self, invoice_id):
        """
        Retrieve an AR invoice based on the provided invoice ID.
        :param invoice_id: ID of the invoice to retrieve.
        :return: A dictionary containing the AR invoice data or an error message.
        """
        # Define search criteria to filter AR invoices
        domain = [
            ('id', '=', invoice_id),
            ('move_type', '=', 'out_invoice'),  # AR invoices have the move_type 'out_invoice'
        ]

        # Retrieve the AR invoice based on the criteria
        invoice = self.env['account.move'].search(domain, limit=1)

        if not invoice:
            return {'error': 'AR invoice not found'}

        # Prepare a list to store invoice line data
        invoice_line_data = []
        for line in invoice.invoice_line_ids:
            invoice_line_data.append({
                'line_id': line.id,
                'product_id': line.product_id.id if line.product_id else False,
                'product_name': line.product_id.name if line.product_id else '',
                'account_id': line.account_id.id,
                'account_name': line.account_id.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'analytic_account_id': line.analytic_account_id.id if line.analytic_account_id else False,
                'analytic_account_name': line.analytic_account_id.name if line.analytic_account_id else '',
            })

        # Assemble AR invoice data
        ar_invoice_data = {
            'id': invoice.id,
            'invoice_number': invoice.name,
            'invoice_date': invoice.invoice_date,
            'due_date': invoice.invoice_date_due,
            'partner_id': invoice.partner_id.id,
            'partner_name': invoice.partner_id.name,
            'amount_total': invoice.amount_total,
            'state': invoice.state,
            'invoice_lines': invoice_line_data,
        }

        # Create a dictionary with an "ar_invoice_info" key
        response = {'ar_invoice_info': ar_invoice_data}

        return response

    @api.model
    def delete_invoice(self, invoice_id):
        invoice = self.env['account.move']
        inv = invoice.search([('id', '=', invoice_id), ('move_type', '=', 'out_invoice')])

        if not inv:
            return "Invoice not found."

        # Check if the bill is posted (validated)
        if inv.state == 'posted':
            # Add logic to cancel related journal entries (if any)
            # Example: bill.button_draft() or bill.button_cancel()
            try:
                inv.button_draft()  # Reset to draft
            except Exception as e:
                return "Failed to reset Invoice to draft: {}".format(e)

        # Additional logic to unreconcile payments if the Invoice is reconciled

        try:
            inv.unlink()  # Delete the bill
            return "Invoice deleted successfully."
        except Exception as e:
            return "Failed to delete bill: {}".format(e)

    @api.model
    def cancel_and_delete_ar_invoice_payment(self, payment_id):
        """
        Cancel and delete an AR invoice payment based on the provided payment ID.
        :param payment_id: ID of the payment to cancel and delete.
        :return: A success message or an error message.
        """
        Payment = self.env['account.move']
        payment = Payment.browse(payment_id)

        if not payment.exists():
            return "Payment not found."

        for pay in payment:
            # Attempt to cancel the payment if it's not already in a cancellable state
            if pay.state not in ['draft', 'cancelled']:
                try:
                    pay.button_draft()
                except UserError as e:
                    return "Failed to cancel payment: {}".format(e)
                except ValidationError as e:
                    return "Validation error occurred: {}".format(e)
                except Exception as e:
                    return "Unexpected error occurred: {}".format(e)

            # Check again if the payment is in a cancellable state after attempting cancellation
            if pay.state in ['draft', 'cancelled']:
                try:
                    pay.unlink()  # Delete the payment
                    return "Payment deleted successfully."
                except Exception as e:
                    return "Failed to delete payment: {}".format(e)
            else:
                return "Payment cannot be deleted as it is not in draft or cancelled state."

        return "Operation completed."  # Return a final message if multiple payments are processed

    @api.model
    def cancel_and_delete_bill_payment(self, payment_id):
        """
        Cancels and deletes a bill payment based on the provided payment ID.

        Parameters:
        payment_id (int): The ID of the payment to be cancelled and deleted.

        Returns:
        str: A message indicating the outcome of the operation.
        """
        Payment = self.env['account.move']
        payment = Payment.browse(payment_id)

        # Check if the payment exists
        if not payment:
            return "Payment not found."

        # Check if the payment is already in a state that allows cancellation
        if payment.state not in ['draft', 'cancelled']:
            try:
                if payment.state == 'posted':
                            payment.button_draft()  # Example method call to reverse the payment
                            payment.write({'state': 'cancelled'})
                else:
                     return "Payment is in a state that cannot be cancelled."

            except UserError as e:
                return f"Failed to cancel payment: {e}"
            except ValidationError as e:
                return f"Validation error occurred: {e}"
            except Exception as e:
                return f"Unexpected error occurred: {e}"

        # Proceed to delete the payment if it is in a cancellable state
        if payment.state in ['draft', 'cancelled']:
            try:
                payment.unlink()
                return "Payment deleted successfully."
            except Exception as e:
                return f"Failed to delete payment: {e}"

        return "Payment cannot be deleted as it is not in a draft or cancelled state."




















