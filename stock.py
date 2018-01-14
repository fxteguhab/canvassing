from openerp.osv import osv


class stock_picking(osv.osv):
	_inherit = 'stock.picking'
	
	def force_assign(self, cr, uid, ids, context=None):
		"""
		Auto transfer pickings with context shipped_or_taken == 'taken'.
		"""
		result = super(stock_picking, self).force_assign(cr, uid, ids, context)
		shipped_or_taken = context.get('shipped_or_taken', False)
		if shipped_or_taken == 'taken':
			self.do_transfer(cr, uid, ids, context)
		return result