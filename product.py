from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

# ===========================================================================================================================

class product_template(osv.Model):
	_inherit = 'product.template'
	_name = 'product.template'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'delivery_expense': fields.float('Delivery Expense'),
	}

# ===========================================================================================================================
