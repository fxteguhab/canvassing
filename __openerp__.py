{
	'name': 'Canvassing',
	'version': '0.1',
	'category': 'Fleet',
	'description': """
		Custom implementation for Toko Besi VIP Bandung
	""",
	'author': 'Christyan Juniady and Associates',
	'maintainer': 'Christyan Juniady and Associates',
	'website': 'http://www.chjs.biz',
	'depends': [
		"base", "board", "web", "website",
		"chjs_custom_view",
		"stock", "account",
	],
	'sequence': 150,
	'data': [
		'views/canvas_view.xml',
		'menu/canvas_menu.xml',
		'report/documents/canvassing_manifest.xml',
		'report/canvassing_report.xml',
	],
	'demo': [
	],
	'test': [
	],
	'installable': True,
	'auto_install': False,
	'qweb': [
	]
}
