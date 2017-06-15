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
	_inherit = 'mail.thread'
	_name = 'canvassing.canvas'
	_description = 'Canvas'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'date_created': fields.datetime('Date Created'),
		'date_depart': fields.datetime('Date Depart'),
		'date_delivered': fields.datetime('Date Delivered'),
		'name': fields.char('Name', readonly=True),
		'driver1': fields.many2one('hr.employee', 'Driver 1'),
		'driver2': fields.many2one('hr.employee', 'Driver 2'),
		'state': fields.selection(_CANVAS_STATE, 'State', readonly=True),
		'trip_expense': fields.one2many('canvassing.canvas.expense', 'canvas_id', 'Trip Expense'),
		'fleet_vehicle': fields.many2one('fleet.vehicle', 'Vehicle'),
		'canvas_stock_line': fields.one2many('canvassing.canvas.stock.line', 'canvas_id', 'Stock Line'),
		'canvas_invoice_line': fields.one2many('canvassing.canvas.invoice.line', 'canvas_id', 'Invoice Line'),
	}
	
# DEFAULTS ------------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'date_created': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
	}

# OVERRIDES -----------------------------------------------------------------------------------------------------------------


# ===========================================================================================================================

class canvasssing_canvas_stock_line(osv.Model):
	_inherit = 'mail.thread'
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
	_inherit = 'mail.thread'
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
	_inherit = 'mail.thread'
	_name = 'canvassing.canvas.expense'
	_description = 'Canvas Expense'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'product_id': fields.many2one('product.product', 'Expense', domain=[('is_expense', '=', True)]),
		'amount': fields.float('Amount'),
	}

# ===========================================================================================================================
