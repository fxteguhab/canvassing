from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp

_CANVAS_STATE = [
	('draft','Draft'),
	('on_the_way','On The Way'),
	('finished','Finished'),
	('canceled','Canceled'),
]

# ===========================================================================================================================

class canvasssing_canvas(osv.Model):
	_name = 'canvassing.canvas'
	_description = 'Canvas'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'name': fields.char('Name', readonly=True),
		'state': fields.selection(_CANVAS_STATE, 'State', readonly=True),
		'date_created': fields.datetime('Date Created', readonly=True),
		'date_depart': fields.datetime('Date Depart', readonly=True),
		'date_delivered': fields.datetime('Date Delivered', readonly=True),
		'driver1_id': fields.many2one('hr.employee', 'Driver 1', required=True),
		'driver2_id': fields.many2one('hr.employee', 'Driver 2'),
		'fleet_vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True),
		'trip_expense_ids': fields.one2many('canvassing.canvas.expense', 'canvas_id', 'Trip Expense'),
		'stock_line_ids': fields.one2many('canvassing.canvas.stock.line', 'canvas_id', 'Stock Line'),
		'invoice_line_ids': fields.one2many('canvassing.canvas.invoice.line', 'canvas_id', 'Invoice Line'),
		'distance': fields.float('Distance'),
	}
	
# DEFAULTS ------------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'date_created': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
	}

# OVERRIDES -----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		vals['name'] = self._get_default_name(cr, uid, vals)
		return super(canvasssing_canvas, self).create(cr, uid, vals, context=context)
	
	def _get_default_name(self, cr, uid, vals):
		driver_name = self.pool.get('hr.employee').browse(cr, uid, [vals.get('driver1_id')]).name
		user_name = self.pool.get('res.users').browse(cr, uid, [uid]).name
		prefix = "%s %s %s" % (datetime.today().strftime('%Y%m%d'), driver_name, user_name)
		canvas_ids = self.search(cr, uid, [('name','=like',prefix+'%')], order='name DESC')
		if len(canvas_ids) == 0:
			last_number = 1
		else:
			canvas_data = self.browse(cr, uid, canvas_ids[0])
			last_number = int(canvas_data.name[-4:]) + 1
		return "%s %04d" % (prefix,last_number)

# ACTIONS ------------------------------------------------------------------------------------------------------------------
	
	def _make_payment(self, cr, uid, partner_id, amount, payment_method, invoice_id, context=None):
		"""
		Register payment. Return
		"""
		if payment_method not in ['transfer', 'cash', 'receivable', 'giro']:
			return False
		
		voucher_obj = self.pool.get('account.voucher')
		journal_obj = self.pool.get('account.journal')
		account_move_line_obj = self.pool.get('account.move.line')
		invoice_obj = self.pool.get('account.invoice')
		
		account_move_id = account_move_line_obj.search(cr, uid, [('invoice', '=', invoice_id)])[0]
		account_move = account_move_line_obj.browse(cr, uid, [account_move_id])
		
		# Prepare voucher values for payment
		voucher_vals = {
			'partner_id': partner_id,
			# 'company_id': 1,
			# 'period_id': 11,
			# 'payment_rate_currency_id': 38,
			# 'date': '2017-10-16',
			# 'payment_rate': 1,
			# 'reference': False,
			# 'writeoff_acc_id': False,
			# 'analytic_id': False,
			# 'is_multi_currency': False,
			# 'narration': False,
			# 'name': False
			'payment_method_type': payment_method,
			'comment': 'Write-Off',
			'payment_option': 'without_writeoff',
			# 'journal_id': 8,
			# 'account_id': 172,
			'pre_line': True,
			'amount': amount,
			'type': 'receipt',
			'line_cr_ids': [(0, False, {
				'date_due': fields.date.today(),
				'reconcile': True if amount >= account_move.debit - account_move.credit else False,
				'date_original': fields.date.today(),
				'move_line_id': account_move.id,
				'amount_unreconciled': account_move.debit - account_move.credit,
				'amount': amount,
				'amount_original': account_move.debit,
				'account_id': account_move.account_id.id
			})],
		}
		
		if payment_method == 'transfer':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['bank'])], limit=1)
			pass
		elif payment_method == 'cash':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['cash'])], limit=1)
			pass
		elif payment_method == 'receivable':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['bank'])], limit=1)
			pass
		elif payment_method == 'giro':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['bank'])], limit=1)
			pass
		
	# Get Default account on branch and change acount_id with it
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		default_account_sales = user_data.default_account_sales_override or user_data.branch_id.default_account_sales
		journal = journal_obj.browse(cr, uid, journal_id, context)
		if default_account_sales:
			voucher_vals.update({
				'account_id': default_account_sales.id}
			)
		else:
			voucher_vals.update({
				'account_id': journal.default_debit_account_id.id or journal.default_credit_account_id.id}
			)

		# Create payment
		voucher_id = voucher_obj.create(cr, uid, voucher_vals, context)
		voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher', context)
		
		# if residual==0, paid
		for invoice in invoice_obj.browse(cr, uid, invoice_id):
			if invoice.residual == 0:
				invoice_obj.write(cr, uid, invoice_id, {'reconciled': True}, context)
				pass

	def action_set_on_the_way(self, cr, uid, ids, context={}):
		for id in ids:
			self.write(cr, uid, [id], {
				'state': 'on_the_way',
				'date_depart': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
			}, context=context)

		# TEGUH@20180329 : tambahan untuk ubah state interbranch jadi state OTW
		interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		for canvas in self.browse(cr, uid, ids, context=context):
			for interbranch_canvas_line in canvas.interbranch_move_ids:
				if interbranch_canvas_line.is_executed:
					interbranch_stock_move_obj.action_otw(cr, uid, [interbranch_canvas_line.interbranch_move_id.id], context=context)


	
	def action_set_finish(self, cr, uid, ids, context={}):
		model_obj = self.pool.get('ir.model.data')
		invoice_obj = self.pool.get('account.invoice')
		invoice_line_obj = self.pool.get('account.invoice.line')
		voucher_obj = self.pool.get('account.voucher')
		voucher_line_obj = self.pool.get('account.voucher.line')
		expense_obj = self.pool.get('hr.expense.expense')
		expense_line_obj = self.pool.get('hr.expense.line')
		canvas_stock_line_obj = self.pool.get('canvassing.canvas.stock.line')
		for canvas_data in self.browse(cr, uid, ids):
			if canvas_data.state in ['finished','canceled']: continue # jangan sampe kefinish dua kali
		# Cek minimal harus ada satu line yg is_executed nya true. Dan kl is_executed nya false, dia harus ada notes nya.
			valid = False
			for stock_line in canvas_data.stock_line_ids:
				if not stock_line.is_executed and (stock_line.notes is False or stock_line.notes == ""):
					raise osv.except_osv(_('Stock Line Error'), _('Please fill the notes why it is not executed.'))
			for invoice_line in canvas_data.invoice_line_ids:
				if not invoice_line.is_executed and (invoice_line.notes is False or invoice_line.notes == ""):
					raise osv.except_osv(_('Invoice Line Error'), _('Please fill the notes why it is not executed.'))
			self.write(cr, uid, [canvas_data.id], {
				'state': 'finished',
				'date_delivered': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
			}, context=context)
			# CREATE EXPENSE
			'''
			new_expense_id = expense_obj.create(cr, uid, {
				'employee_id': canvas_data.driver1_id.id,
				'date': canvas_data.date_delivered,
				'name': canvas_data.name,
			})
			for expense_line in canvas_data.trip_expense_ids:
				expense_line_obj.create(cr, uid, {
					'expense_id': new_expense_id,
					'product_id': expense_line.product_id.id,
					'date_value': canvas_data.date_delivered,
					'name': canvas_data.name,
					'uom_id': expense_line.product_id.uom_id.id,
					'unit_amount': expense_line.amount,
					'unit_quantity': 1.0,
				})
			'''
			# CREATE ONGKIR
			# Check if there's stock picking id or not (because it's not required)
			for stock_line in canvas_data.stock_line_ids:
				if (stock_line.stock_picking_id) and (stock_line.is_executed):
					# Transfer pickings
					if (stock_line.stock_picking_id.picking_type_id.code == 'outgoing'):
						stock_line.stock_picking_id.do_transfer()
					'''
					if  (stock_line.delivery_amount >0):
					# only if there is, then create invoice
						new_invoice_id = invoice_obj.create(cr, uid, {
							'partner_id': stock_line.stock_picking_id.partner_id.id,
							'date_invoice': canvas_data.date_delivered,
							'account_id': stock_line.stock_picking_id.partner_id.property_account_receivable.id,
							'fiscal_position': stock_line.stock_picking_id.partner_id.property_account_position.id,
							'supplier_invoice_number': 'Delivery Fee :'+ canvas_data.name,
						})
						model, product_id = model_obj.get_object_reference(cr, uid, 'canvassing', 'canvassing_product_delivery_fee')
						invoice_line_obj.create(cr, uid, {
							'invoice_id': new_invoice_id,
							'product_id': product_id,
							'name': canvas_data.name,
							'price_unit': stock_line.delivery_amount,
							'quantity': 1.0,
						})
						canvas_stock_line_obj.write(cr, uid, [stock_line.id], {
							'delivery_fee_invoice_id': new_invoice_id,
						}, context=context)
						
						#validate invoice
						invoice_obj.signal_workflow(cr, uid, [new_invoice_id], 'invoice_open', context)
						self._make_payment(cr, uid, stock_line.stock_picking_id.partner_id.id, stock_line.delivery_amount, 'cash',[new_invoice_id], context=None)
					'''
			'''
			# PAY INVOICE
			for invoice_line in canvas_data.invoice_line_ids:
				if invoice_line.is_executed:
					inv = invoice_line.invoice_id
					move_line_id = 0
					for move_line in inv.move_id.line_id:
						if inv.type == 'in_invoice':
							move_line_id = move_line.id if move_line.debit == 0 else move_line_id
						else:
							move_line_id = move_line.id if move_line.credit == 0 else move_line_id
					new_voucher_id = voucher_obj.create(cr, uid, {
						'partner_id': inv.partner_id.id,
						'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
						'account_id': inv.account_id.id,
						'journal_id': invoice_line.journal_id.id,
						'type': 'receipt' if inv.type == 'out_invoice' else 'payment',
						'reference': canvas_data.name,
						'date': canvas_data.date_delivered,
						'pay_now': 'pay_now',
						'date_due': canvas_data.date_delivered,
						'line_dr_ids': [(0, False, {
							'type': 'dr' if inv.type == 'in_invoice' else 'cr',
							'account_id': inv.account_id.id,
							'partner_id': inv.partner_id.id,
							'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
							'move_line_id': move_line_id,
							'reconcile': True,
						})]
					})
					voucher_obj.proforma_voucher(cr, uid, [new_voucher_id])
			
			'''
# ===========================================================================================================================

class canvasssing_canvas_stock_line(osv.Model):
	_name = 'canvassing.canvas.stock.line'
	_description = 'Canvas Stock Line'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'stock_picking_id': fields.many2one('stock.picking', 'Stock Picking', domain=[('state', '=', 'assigned')]),
		'address': fields.text('Address', required=True),
		'is_executed': fields.boolean('Is Executed'),
		'delivery_amount': fields.float('Delivery Fee'),
		'delivery_fee_invoice_id': fields.many2one('account.invoice', 'Delivery Fee Invoice',
			readonly=True, domain=[('state', '!=', 'done')]),
		'notes': fields.text('Notes'),
		'canvas_state': fields.related('canvas_id', 'state', type='char', string='Canvas State'),
		'partner_id' : fields.many2one('res.partner','Partner'), 
	}

# ONCHANGE ------------------------------------------------------------------------------------------------------------------
	
	def onchange_stock_picking(self, cr, uid, ids, stock_picking_id, context=None):
		result = {}
		result['value'] = {}
		if stock_picking_id:
			try:
				stock_picking_obj = self.pool.get('stock.picking')
				stock_picking = stock_picking_obj.browse(cr, uid, stock_picking_id)
				if stock_picking:
					sale_order_obj = self.pool('sale.order')
					sale_order_id = sale_order_obj.search(cr,uid,[('picking_ids', '=', stock_picking_id)], limit=1)
					sale_order = sale_order_obj.browse(cr, uid, sale_order_id)
					if sale_order.customer_address and len(sale_order.customer_address) > 0:
						result['value'].update({
							'address': sale_order.customer_address.replace('\n',' '),
							'partner_id' : sale_order.partner_id.id,
						})
					else:
						result['value'].update({
							'address': stock_picking.partner_id.contact_address.replace('\n',' '),
							'partner_id' : sale_order.partner_id.id,
						})
			except Exception, e:
				result['value'].update({
					'address': '',
				})
				result['warning'] = {
					'title': e.name,
					'message': e.value,
				}
			finally:
				return result
		return result
	
# ===========================================================================================================================

class canvasssing_canvas_invoice_line(osv.Model):
	_name = 'canvassing.canvas.invoice.line'
	_description = 'Canvas Invoice Line'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice',  domain=[('state', '=', 'open')]),
		'address': fields.text('Address', required=True),
		'invoice_total': fields.float("Total", digits_compute=dp.get_precision('Account'), readonly=True),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True, domain=[('type', '=', 'cash')]),
		'is_executed': fields.boolean('Is Executed'),
		'notes': fields.text('Notes'),
		'canvas_state': fields.related('canvas_id', 'state', type='char', string='Canvas State'),
	}
	
# DEFAULTS ------------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'journal_id': lambda self, cr, uid, *a: self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash')])[0]
	}
	
# ONCHANGE ------------------------------------------------------------------------------------------------------------------
	
	def onchange_invoice_id(self, cr, uid, ids, invoice_id, context=None):
		result = {}
		result['value'] = {}
		if invoice_id:
			try:
				invoice_obj = self.pool.get('account.invoice')
				invoice = invoice_obj.browse(cr, uid, invoice_id)
				if invoice:
					sale_order_obj = self.pool('sale.order')
					sale_order_id = sale_order_obj.search(cr,uid,[('invoice_ids', '=', invoice_id)], limit=1)
					sale_order = sale_order_obj.browse(cr, uid, sale_order_id)
					if sale_order.customer_address and len(sale_order.customer_address) > 0:
						result['value'].update({
							'address': sale_order.customer_address.replace('\n',' ')
						})
					else:
						result['value'].update({
							'address': invoice.partner_id.contact_address.replace('\n',' ')
						})
					result['value'].update({
						'invoice_total': invoice.residual
					})
			except Exception, e:
				result['value'].update({
					'address': '',
				})
				result['warning'] = {
					'title': e.name,
					'message': e.value,
				}
			finally:
				return result
		return result

# ===========================================================================================================================

class canvasssing_canvas_expense(osv.Model):
	_name = 'canvassing.canvas.expense'
	_description = 'Canvas Expense'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'product_id': fields.many2one('product.product', 'Expense', domain=[('hr_expense_ok', '=', True)]),
		'amount': fields.float('Amount'),
	}

# ===========================================================================================================================
