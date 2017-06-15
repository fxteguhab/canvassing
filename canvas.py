from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

# ===========================================================================================================================

class canvasssing_canvas(osv.Model):
	_inherit = 'mail.thread'
	_name = 'canvassing.canvas'
	_description = 'Canvas'

	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	_columns = {
		'name': fields.char('Name', required=True),
		'is_used': fields.boolean('Is Used'),
		'algorithm': fields.text('Algorithm', required=True),
	}

# DEFAULTS ------------------------------------------------------------------------------------------------------------------

	_defaults = {
		'is_used': False,
		'algorithm': "def calculate_needs(supplier_id):\n	return []",
	}

# OVERRIDES -----------------------------------------------------------------------------------------------------------------


# ===========================================================================================================================
