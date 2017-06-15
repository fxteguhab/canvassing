from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

# ===========================================================================================================================

class purchase_needs_algorithm(osv.Model):
	_inherit = 'mail.thread'
	_name = 'purchase.needs.algorithm'
	_description = 'Purchase Needs Algorithm'

	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	_columns = {
		'name': fields.char('Name', required=True),
		'is_used': fields.boolean('Is Used'),
		'algorithm': fields.text('Algorithm', required=True),
	}

	# DEFAULTS --------------------------------------------------------------------------------------------------------------

	_defaults = {
		'is_used': False,
		'algorithm': "def calculate_needs(supplier_id):\n	return []",
	}

	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def create(self, cr, uid, data, context=None):
		new_algorithm = super(purchase_needs_algorithm, self).create(cr, uid, data, context)
		algorithm_ids = self.search(cr, uid, [('id', '!=', new_algorithm)])
		if len(algorithm_ids) == 0:
			if data['is_used'] == False:
				self.write(cr, uid, [new_algorithm], {'is_used': True}, context)
		else:
			if data['is_used'] == True:
				for algorithm in self.browse(cr, uid, algorithm_ids):
					if algorithm.is_used == True:
						self.write(cr, uid, [algorithm.id], {'is_used': False}, context)
						break
		return new_algorithm

	def write(self, cr, uid, ids, data, context=None):
		result = super(purchase_needs_algorithm, self).write(cr, uid, ids, data, context)
		if 'is_used' in data and data['is_used'] == True:
			algorithm_ids = self.search(cr, uid, [('id', '!=', ids)])
			for algorithm_id in algorithm_ids:
				algorithm = self.browse(cr, uid, [algorithm_id])
				if algorithm.is_used == True:
					self.write(cr, uid, [algorithm_id], {'is_used': False}, context)
		return result

	def unlink(self, cr, uid, ids, context=None):
		result = super(purchase_needs_algorithm, self).unlink(cr, uid, ids, context)
		algorithm_ids = self.search(cr, uid, [])
		if len(algorithm_ids) == 1:
			for algorithm in self.browse(cr, uid, algorithm_ids):
				if algorithm.is_used == False:
					self.write(cr, uid, [algorithm.id], {'is_used': True}, context)
		return result


# ===========================================================================================================================


class purchase_needs(osv.Model):
	_inherit = 'mail.thread'
	_name = 'purchase.needs'
	_description = 'Purchase Needs'

	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------

	def _compute_rate_number_selected_unselected(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		need_line_obj = self.pool.get('purchase.needs.line')
		for record in self.browse(cr, uid, ids, context=context):
			counter_selected = 0
			need_line_ids = need_line_obj.search(cr, uid, [('purchase_needs_id', '=', record.id)])
			for need_line_id in need_line_ids:
				need_line = need_line_obj.browse(cr, uid, [need_line_id])
				if need_line.is_selected == True:
					counter_selected += 1
			if len(need_line_ids) == 0:
				percentage_selected = 0.00
			else:
				percentage_selected = (counter_selected * 100.00) / len(need_line_ids)
			result[record.id] = {
				'selected' : counter_selected,
				'unselected' : len(need_line_ids) - counter_selected,
				'total' : len(need_line_ids),
				'selection_rate' : percentage_selected
			}
		return result

	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	_columns = {
		'supplier_id': fields.many2one('res.partner', required=True, string='Supplier', domain=[('supplier', '=', 'True')],
			ondelete='restrict'),
		'target_date': fields.date('Target Date', required=True),
		'algorithm_id': fields.many2one('purchase.needs.algorithm', string='Algorithm', ondelete='SET NULL'),
		'need_line_ids': fields.one2many('purchase.needs.line', 'purchase_needs_id', 'Need Line'),
		'selection_rate': fields.function(_compute_rate_number_selected_unselected, string="Selection Rate",
			type='float', store=True, multi='compute_selected_unselected'),
		'selected' : fields.function(_compute_rate_number_selected_unselected, string="Number of Selected",
			type='integer', store=True, multi='compute_selected_unselected'),
		'unselected' : fields.function(_compute_rate_number_selected_unselected, string="Number of unselected",
			type='integer', store=True, multi='compute_selected_unselected'),
		'total' : fields.function(_compute_rate_number_selected_unselected, string="Total Line",
			type='integer', store=True, multi='compute_selected_unselected'),
	}

	# METHODS ---------------------------------------------------------------------------------------------------------------

	def _pool_generate_po_vals(self, cr, uid, context, need):
		"""
		Pool all required data from this Needs to create a PO
		:param need: a recordset of purchase.need
		:return: a dictionary that will be passed as the 'vals' parameter to create a PO
		"""
		order_line_vals = []
		for need_line in need.need_line_ids:
			if need_line.is_selected:
				purchase_order_line_vals = {
					'product_id': need_line.product_id.id,
					'name': need_line.product_id.name,
					'date_planned': need.target_date,
					'product_qty': need_line.qty,
					'price_unit': need_line.product_id.standard_price,
					'purchase_needs_id': need.id,
					'source': 'needs',
				}
				order_line_vals.append((0, False, purchase_order_line_vals))
		if len(order_line_vals) == 0:
			raise osv.except_orm(_('Needs Error'), _('There is no Need marked as selected.'))
		return {
			# Purchase Order defaults
			'date_order': datetime.now(),
			# 'name': '/',
			'shipped': 0,
			'invoice_method': 'order',
			'invoiced': 0,
			'location_id': self.pool.get('res.partner')
				.browse(cr, uid, self.pool.get('res.users')._get_company(cr, uid, context))
				.property_stock_customer.id,
			'pricelist_id': self.pool.get('res.partner').browse(cr, uid, [
				need.supplier_id.id]).property_product_pricelist_purchase.id,
			'company_id': self.pool.get('res.users')._get_company(cr, uid, context),
			'journal_id': self.pool.get('purchase.order')._get_journal(cr, uid, context),
			'currency_id': self.pool.get('res.users').browse(cr, uid, uid, context).company_id.currency_id.id,
			'picking_type_id': self.pool.get('purchase.order')._get_picking_in(cr, uid, context),
			# Added params from purchase needs
			'partner_id': need.supplier_id.id,
			'purchase_needs_id': need.id,
			'order_line': order_line_vals,
		}

	# ACTIONS ---------------------------------------------------------------------------------------------------------------

	def action_generate_needs(self, cr, uid, ids, supplier_id, context=None):
		if supplier_id:
			algorithm_obj = self.pool.get('purchase.needs.algorithm')
			active_algorithm_ids = algorithm_obj.search(cr, uid, [('is_used', '=', True)])
			if len(active_algorithm_ids) == 0:
				raise osv.except_orm(_('Needs Error'), _('There is no Purchase Needs Algorithm marked as being used.'))
			active_algorithm = algorithm_obj.browse(cr, uid, active_algorithm_ids)
			try:
				exec active_algorithm.algorithm
				# noinspection PyUnresolvedReferences
				needs = calculate_needs(supplier_id)
			except:
				raise osv.except_orm(_('Needs Error'), _('Syntax or other error(s) in the code of selected Need Algorithm.'))
			needs_line = []
			for need in needs:
				needs_line.append((0, False, need))
			return {'value': {'need_line_ids': needs_line, 'algorithm_id': active_algorithm.id}}

	def action_generate_po(self, cr, uid, ids, context=None):
		purchase_order_obj = self.pool.get('purchase.order')
		new_purchase_order_ids = []
		for need in self.browse(cr, uid, ids):
			if len(need.need_line_ids) != 0:
				counter_selected = 0
				for need_line in need.need_line_ids:
					if need_line.is_selected:
						counter_selected += 1
				if counter_selected == 0:
					raise osv.except_orm(_('Generate PO Error'), _('You must select at least one product in Need Lines'))
				else:
					vals = self._pool_generate_po_vals(cr, uid, context, need)
					supplier_draft_po_id = purchase_order_obj.search(cr, uid, [('partner_id', '=', need.supplier_id.id),
																			   ('state', '=', 'draft')],
																	 order = 'date_order desc')
					if len(supplier_draft_po_id) == 0:
						new_purchase_order_id = purchase_order_obj.create(cr, uid, vals, context)
					else:
						new_purchase_order_id = supplier_draft_po_id[0]
						purchase_orders = purchase_order_obj.browse(cr, uid, [new_purchase_order_id])
						purchase_order_line_obj = self.pool.get('purchase.order.line')
						# Check if there is same product, don't create new purchase order line
						for purchase_order in purchase_orders:
							for order_line in vals['order_line']:
								order_line_obj = order_line[2]
								order_line_obj['order_id'] = purchase_order.id
								same_product = False
								for purchase_order_line in purchase_order.order_line:
									if order_line_obj['product_id'] == purchase_order_line.product_id.id:
										same_product = True
										purchase_order_line_obj.write(cr, uid, [purchase_order_line.id],
																	  {'product_qty': order_line_obj['product_qty'] +
																					  purchase_order_line.product_qty}
																	  , context)
								if same_product == False:
									purchase_order_line_obj.create(cr, uid, order_line_obj, context)

					new_purchase_order_ids.append(new_purchase_order_id)
					self.write(cr, uid, [need.id], context)
					action = {"type": "ir.actions.act_window", "res_model": "purchase.order"}
					if len(new_purchase_order_ids) == 1:
						action.update({"views": [[False, "form"]], "res_id": new_purchase_order_ids[0]})
					else:
						action.update({"views": [[False, "tree"], [False, "form"]], "domain": [["id", "in", new_purchase_order_ids]]})
					return action
			else:
				raise osv.except_orm(_('Generate PO Error'), _('You must have at least one product in Need Lines'))

	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def name_get(self, cr, uid, ids, context=None):
		result = []
		for record in self.browse(cr, uid, ids):
			name = record.target_date + ' - ' + record.supplier_id.name
			result.append((record.id, name))
		return result

# ===========================================================================================================================

class purchase_needs_line(osv.Model):
	_inherit = 'mail.thread'
	_name = 'purchase.needs.line'
	_description = 'Purchase Needs Line'

	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	_columns = {
		'purchase_needs_id': fields.many2one('purchase.needs', string='Purchase Needs'),
		'product_id': fields.many2one('product.product', required=True, string='Product',
									  domain=[('purchase_ok', '=', 'True')], ondelete='restrict'),
		'qty': fields.float('Quantity'),
		'is_selected': fields.boolean('Is Selected'),
	}

	# DEFAULTS ---------------------------------------------------------------------------------------------------------------

	_defaults = {
		'is_selected': False,
	}

# ===========================================================================================================================


class purchase_order(osv.Model):
	_inherit = 'purchase.order'

	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	_columns = {
		'purchase_needs_id': fields.many2one('purchase.needs', 'Need', readonly=True, ondelete='set null'),
	}

	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def unlink(self, cr, uid, ids, context=None):
		# Check if the purchase order has a purchase_needs_id, cancel the unlink
		for po in self.browse(cr, uid, ids):
			if po.purchase_needs_id:
				raise osv.except_orm(_('Purchase Order Error'),
									 _('This Purchase Order has been linked to a Purchase Need, so it cannot be deleted.'))
		result = super(purchase_order, self).unlink(cr, uid, ids, context)
		return result
