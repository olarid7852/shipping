{ 
    'name': "Shipping",
    'summary': "Manage your shipping",
    'description': """Long description""", 
    'author': "Your name", 
    'website': "http://www.example.com", 
    'category': 'Uncategorized', 
    'version': '12.0.1', 
    'depends': ['base', 'web', 'account', 'l10n_us', 'om_account_accountant', 'stock'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/library_book.xml',
        'views/shipping_list.xml',
        'views/aircargo_shipping_list.xml',
        'views/menu_items.xml'
    ],
    # 'demo': ['demo.xml'], 
} 
