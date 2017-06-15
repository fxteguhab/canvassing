from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

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
		'date_created': fields.datetime('Date Created'),
		'date_depart': fields.datetime('Date Depart'),
		'date_delivered': fields.datetime('Date Delivered'),
		'driver1_id': fields.many2one('hr.employee', 'Driver 1'),
		'driver2_id': fields.many2one('hr.employee', 'Driver 2'),
		'fleet_vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle'),
		'trip_expense_ids': fields.one2many('canvassing.canvas.expense', 'canvas_id', 'Trip Expense'),
		'stock_line_ids': fields.one2many('canvassing.canvas.stock.line', 'canvas_id', 'Stock Line'),
		'invoice_line_ids': fields.one2many('canvassing.canvas.invoice.line', 'canvas_id', 'Invoice Line'),
	}
	
# DEFAULTS ------------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'date_created': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
	}

# ACTIONS ------------------------------------------------------------------------------------------------------------------
	
	def action_set_on_the_way(self, cr, uid, ids, context={}):
		for id in ids:
			self.write(cr, uid, [id], {
				'state': 'on_the_way',
				'date_depart': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
			}, context=context)
	
	def action_set_finish(self, cr, uid, ids, context={}):
		for canvas_data in self.browse(cr, uid, ids):
		# Cek minimal harus ada satu line yg is_executed nya true. Dan kl is_executed nya false, dia harus ada notes nya.
			valid = False
			for stock_line in canvas_data.stock_line_ids:
				if stock_line.is_executed:
					valid = True
				else:
					if stock_line.notes == False or stock_line.notes == "":
						raise osv.except_osv(_('Stock Line Error'),_('Please fill the notes why it is not executed.'))
			for invoice_line in canvas_data.invoice_line_ids:
				if invoice_line.is_executed:
					valid = True
				else:
					if invoice_line.notes == False or invoice_line.notes == "":
						raise osv.except_osv(_('Invoice Line Error'),_('Please fill the notes why it is not executed.'))
			if valid:
				self.write(cr, uid, [canvas_data.id], {
					'state': 'finished',
					'date_delivered': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
				}, context=context)

# ===========================================================================================================================

class canvasssing_canvas_stock_line(osv.Model):
	_name = 'canvassing.canvas.stock.line'
	_description = 'Canvas Stock Line'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'stock_picking_id': fields.many2one('stock.picking', 'Stock Picking', domain=[('state', '!=', 'done')]),
		'address': fields.text('Name', required=True),
		'is_executed': fields.boolean('Is Executed'),
		'distance': fields.float('Distance'),
		'deliver_amount': fields.float('Delivery Amount'),
		'delivery_fee_invoice_id': fields.many2one('account.invoice', 'Delivery Fee Invoice',
			readonly=True, domain=[('state', '!=', 'done')]),
		'notes': fields.text('Notes'),
	}

# OVERRIDES -----------------------------------------------------------------------------------------------------------------


# ===========================================================================================================================

class canvasssing_canvas_invoice_line(osv.Model):
	_name = 'canvassing.canvas.invoice.line'
	_description = 'Canvas Invoice Line'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice'),
		'address': fields.text('Name', required=True),
		'is_executed': fields.boolean('Is Executed'),
		'distance': fields.float('Distance'),
		'notes': fields.text('Notes'),
	}

# ===========================================================================================================================

class canvasssing_canvas_expense(osv.Model):
	_name = 'canvassing.canvas.expense'
	_description = 'Canvas Expense'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'product_id': fields.many2one('product.product', 'Expense', domain=[('is_expense', '=', True)]),
		'amount': fields.float('Amount'),
	}

# ===========================================================================================================================
