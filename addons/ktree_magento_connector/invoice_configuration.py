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
#from common_tools import *
import traceback
from pprint import pprint
import base64, urllib
from openerp.tools.translate import _

#inherit magento_configuration class to add invoice export function
class magento_configuration(osv.osv):
    _inherit = 'magento.configuration'
    #this function is use to export invoice from openerp to magento
    def export_invoice(self,cr,uid):
        total_no_of_records=0#Count number of  Exported Invoice
        
            # magneto object through which connecting openerp with defined magneto configuration start 
        [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
        if not status:
                raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                    please check the url,username and password") )
                return -1
            #End
        try:     
            #Searching all sale order from openerp
            sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('magento_increment_id' ,'!=', None)])
            #Creating object for above selected sale order.
            sale_order_obj = self.pool.get('sale.order').browse(cr, uid, sale_order_ids)
            for sale_order in sale_order_obj:
                #API to get all sale order information from magneto
                order = server.call(session, 'order.info', [sale_order.magento_increment_id])
                for invoice in sale_order.invoice_ids:
                    #searching status of invoice from openerp and getting all information to update in magneto
                    if invoice.state != 'draft' and not invoice.magento_increment_id:
                        dict = {}
                        invoice_line_id = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id' ,'=', invoice.id)])
                        invoice_line_obj = self.pool.get('account.invoice.line').browse(cr, uid,invoice_line_id )
                        for invoice_line in invoice_line_obj:
                            magento_product_id = invoice_line.product_id.magento_id
                            for item in order.get('items'):
                                if item['product_id'] == str(magento_product_id) :
                                    dict[item['item_id']] = int(invoice_line.quantity)
#                        if invoice.state=='open':    
#                                                state=1
#                        if invoice.state=='paid':
#                                                 state=2
#                        if invoice.state=='cancel':      
#                                                state=3     
                        try: 
                           #API to create invoice in magneto     
                           magento = server.call(session, 'sales_order_invoice.create', [sale_order.magento_increment_id, dict, '', False, False]) 
                           if magento:
                              total_no_of_records+=1
                           #update magento_increment_id in openerp in invoice object    
                           self.pool.get('account.invoice').write(cr, uid, invoice.id,{'magento_increment_id' : magento}) 
                        except:
                            pass
            return total_no_of_records
        except:
            return -1
    
magento_configuration() 

#Configured account object based on magneto
class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'magento_increment_id' : fields.char('Magento Increment ID',size=64),
        'magento_shipment_id' : fields.char('Magento Shipment ID',size=64),
    }  

account_invoice()       