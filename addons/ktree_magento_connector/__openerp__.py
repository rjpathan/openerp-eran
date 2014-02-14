# 2012-Magneto Connector Ktree Organisation (http://www.ktree.com).
#This is Free Software: Very User Friendly 
#Using this module we can import and export information from magneto
{
    "name" : "Magento-OpenERP Synchronization",
    "version" : "1.0",
    "author" : "Ktree Organization",
    "website" : "http://www.ktree.com/",
    "depends" : ["product", "stock", "sale", "account", "account_analytic_default",'product_images_olbs',],
    "description": "To enable open ERP to access the resources in magento and synchronize",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" :  [
                     'wizard/magento_products_import_view.xml',
                     'wizard/magento_categories_import_view.xml',
                     'wizard/magento_customer_import_view.xml',
                     'wizard/magento_orders_import_view.xml',
                     'wizard/magento_stock_import_view.xml',
                     'wizard/magento_category_export_view.xml',
                     'wizard/magento_products_export_view.xml',
                     'wizard/magento_stock_export_view.xml',
                     'wizard/magento_customer_export_view.xml',
                     'wizard/magento_delivery_export_view.xml',
                     'wizard/magento_invoice_export_view.xml',
                     'wizard/magento_credit_memo_import_view.xml',
                     'magento_configuration_view.xml',
                     'product_configuration.xml',
                     'product_images_view.xml',
                     'partner_configuration.xml',
                     ],
    "active": False,
    "installable": True
}
