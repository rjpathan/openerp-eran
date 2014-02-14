# 2012-Magneto Connector Ktree Organisation (http://www.ktree.com).
#Using this file, we can configure all magneto instance and based on magneto configuration we will make server connector

from osv import fields,osv
from mx import DateTime
import netsvc
import tools
import pooler
import time
import datetime
import math
import os
import traceback
from pprint import pprint
import sys
import wizard
import xmlrpclib
from xmlrpclib import ServerProxy, Error
import threading

class magento_configuration(osv.osv):
    _name = 'magento.configuration'
    _description = 'Magento Configuration information'
    _columns = {
        'name' : fields.char('Name', size=128), 
        'url' : fields.char('Magento base URL', size=128), 
        'api_user' : fields.char('API User', size=64),
        'api_pwd' : fields.char('API Password', size=64),
        'auto_export_stock' : fields.boolean('Automatic stock export'),
        'auto_export_products' : fields.boolean('Automatic products export'),
        'auto_import_products' : fields.boolean('Automatic products import'),
        'auto_import_orders' : fields.boolean('Automatic orders import'),
        'auto_import_credit_memos' : fields.boolean('Automatic credit memos import'),
        'auto_script_path' : fields.char('Syncronization Script Path', size=256),
        'sync_sleep' : fields.integer('Time between synchronizations'),
        'sync_script_pid' : fields.integer('PID of Sync Script'),
        'sync_status' : fields.char('Synchronisation status', size=128),
        'shipping_product' : fields.many2one('product.product', 'Shipping Product', required=True, change_default=True),
        'default_category' : fields.many2one('product.category', 'Default category for imported products', required=True, change_default=True),
        'magento_root_cat_id' : fields.integer('Magento Root category ID'),
        'last_imported_product_timestamp' : fields.char('Timestamp of latest imported product', size=128),
        'last_imported_category_timestamp' : fields.char('Timestamp of latest imported category', size=128),
        'last_imported_invoice_timestamp' : fields.char('Timestamp of latest imported invoice', size=128),
        'payment_journal' : fields.many2one('account.journal', 'Payment Journal'),  
        'last_invoice_id' : fields.integer('Last imported sale order'),
        'last_creditmemo_id' : fields.integer('Last imported credit memo'),
        'auto_invoice_open' : fields.boolean('Imported invoices automatically goes to Open state'),
        'auto_invoice_paid' : fields.boolean('Imported invoices automatically goes to Paid state'),
        'inital_stock_location' : fields.many2one('stock.location', 'Location for stock initialization'),
        'import_credit_memos' : fields.boolean('Import credit memos after importing orders'),
        'last_imported_customer_timestamp' : fields.char('Timestamp of latest imported Customer', size=128),              
        'last_updated_order_timestamp'    : fields.char('Timestamp of latest updated', size=128),
        'last_exported_order_timestamp'   : fields.char('Timestamp of latest exported order', size=128),
        'import_delivery'                 : fields.boolean('Import shipping after importing orders'),
        'import_invoice'                  : fields.boolean('Import invoice after importing orders'),
        'max_number_order_import'         : fields.char('Max.No. Order Import/Connection',size=128,help='Indicate Number of Sale Order Import Per Connection,By default 20'),
        'max_number_product_import'       : fields.char('Max.No. Product Import/Connection',size=128,help='Indicate Number of Product Import Per Connection,By default 500'),
        'max_number_customer_import'       : fields.char('Max.No. Customer Import/Connection',size=128,help='Indicate Number of Customer Import Per Connection,By default 500'),
        'last_imported_credit_timestamp' :fields.char('Timestamp of latest imported Creditmemo', size=128),
    }
    _defaults = {
        'auto_export_stock': lambda *a: False,
        'auto_export_products': lambda *a: False,
        'auto_import_products': lambda *a: False,
        'auto_import_orders': lambda *a: False,
        'auto_import_credit_memos': lambda *a: False,
        'sync_sleep': lambda *a: 300,
        'sync_script_pid': lambda *a: -1,
        'last_creditmemo_id' : lambda *a: -1,
        'last_invoice_id': lambda *a: -1,
        'sync_status': lambda *a: 'Idle',
        'last_imported_invoice_timestamp': lambda *a: '2011-01-01',
        'magento_root_cat_id': lambda *a: -1,
        'auto_invoice_open': lambda *a: False,
        'auto_invoice_paid': lambda *a: False,
    }
    #Constraints for one Magneto Configuration
    def _unique(self, cr, uid, ids):
        res = self.pool.get('magento.configuration').search(cr, uid,[])
        if len(res) > 1 :
            return False
        else :
            return True
    
    _constraints = [
        (_unique, 'Only one Magneto Configuration supported at this time.', [])
    ]
    
    ####to get magento configuration reference##############################################################  
    def get_magento_configuration_object(self, cr, uid):
        try:
            website_ids = self.pool.get('magento.configuration').search(cr, uid, [])
            magento_params = self.pool.get('magento.configuration').browse(cr, uid, [website_ids[0]])
            return magento_params
        except:
            pass
    #to get the magneto server and session based on API USER and API PASSWORD
    def magento_openerp_syn(self, cr, uid):
        try:
            #To search magneto configuration id from openerp
            ids = self.pool.get('magento.configuration').search(cr, uid, [])
            #To create reference
            config_obj = self.pool.get('magento.configuration').browse(cr, uid, [ids[0]])
            #configured url for magneto
            server_address = config_obj[0]['url']
            if not server_address[-1:] == '/':
                server_address = server_address + "/"
            server_address = server_address + "index.php/api/xmlrpc/?wsdl"
            server = ServerProxy(server_address)
            #To login with magneto for configured API user
            session = server.login(config_obj[0]['api_user'], config_obj[0]['api_pwd'])
            return [True, server, session]
        except Exception,e:
            return [False, sys.exc_info()[0], False]
    
    #to get status of auto synchronization for import/export function. 
    def get_auto_syn_status(self, cr, uid):
        try:
            website_ids = self.pool.get('magento.configuration').search(cr, uid, [])
            magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
            return {'sync_sleep': magento_configuration_object[0].sync_sleep, 
                'auto_export_stock': magento_configuration_object[0].auto_export_stock,
                'auto_export_products': magento_configuration_object[0].auto_export_products, 
                'auto_import_products': magento_configuration_object[0].auto_import_products, 
                'auto_import_orders': magento_configuration_object[0].auto_import_orders, 
                'auto_import_credit_memos': magento_configuration_object[0].auto_import_credit_memos,
                'sync_script_pid': magento_configuration_object[0].sync_script_pid,
            }
        except:
            return -1    
    #To get tax information while importing sale order
    def get_tax_id(self, cr, uid, rate):   
            rate = float(rate) / 100
            rate=round(rate,2)
            list_tax_ids = self.pool.get('account.tax').search(cr, uid, [('amount' , "=", rate), ('type_tax_use', "=", 'sale'),('description' , "ilike", 'Magento')])
            if (list_tax_ids == []):
                tax = {'name': ('Tax ' + str(rate*100) + '%'),
                                'amount': round(rate,2),
                                'type': 'percent',
                                'description': ('Magento' + str(rate*100) + '%'),
                                'price_include': True,
                                'type_tax_use': 'sale',
                }    
                tax_id = self.pool.get('account.tax').create(cr, uid, tax)
            else:
                #should add a check in case of sevral taxes
                tax_id = list_tax_ids[0]
            return tax_id

magento_configuration()

