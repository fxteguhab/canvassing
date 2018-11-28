from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime
# ==========================================================================================================================

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
	_columns = {
		'shipped_or_taken': fields.selection([
			('taken', 'Pick-Up'),
			('shipped', 'Delivery'),
		], 'Pick-Up / Delivery', readonly="True", states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
		'customer_address': fields.char('Customer Address'),
		'delivery_date': fields.datetime('Delivery Date'),
	}
	
	# DEFAULTS ------------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'delivery_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
	}

	# WORKFLOWS -------------------------------------------------------------------------------------------------------------
	
	def action_ship_create(self, cr, uid, ids, context=None):
		"""
		Force availability created pickings
		"""
		if context is None:
			context = {}
		result = super(sale_order, self).action_ship_create(cr, uid, ids, context)
		picking_obj = self.pool.get('stock.picking')
		pick_ids = []
		shipped_or_taken = False
		for so in self.browse(cr, uid, ids, context=context):
			pick_ids += [picking.id for picking in so.picking_ids]
			shipped_or_taken = so.shipped_or_taken
		context = context.copy()
		context.update({'shipped_or_taken': shipped_or_taken})
		picking_obj.force_assign(cr, uid, pick_ids, context)
		return result
