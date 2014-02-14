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
import base64, urllib
from openerp.tools.translate import _
#inherit magento_configuration class to add stock import function
class magento_configuration(osv.osv):
    _inherit = 'magento.configuration'
    
    # This function is use to export delivery from openerp to magento
    def export_delivery(self,cr,uid):
        total_no_of_records=0#Count number of Delivery orders Exported  
        try:
            # magneto object through which connecting openerp with defined magneto configuration start 
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
            if not status:
                set_export_finished()  
                return -1
        except :
             raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password") )
            #End
        try:     
            #Searching Sale order from Openerp
            sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('magento_increment_id' ,'!=', None)])
            #Creating Sale Order Object based on all above sale order ids
            sale_order_obj = self.pool.get('sale.order').browse(cr, uid, sale_order_ids)
            for sale_order in sale_order_obj:
                #API to fetching all sale order information based on magento_increment_id from magneto
                order = server.call(session, 'order.info', [sale_order.magento_increment_id])
                for picking in sale_order.picking_ids:
                    #Checking status of Delivery order for Specific sale order in openerp
                    if picking.state == 'done' and not picking.magento_increment_id:
                        dict1 = {}
                        #searching all stock move and getting all information  for particular delivery order,from openerp start
                        move_id = self.pool.get('stock.move').search(cr, uid, [('picking_id' ,'=', picking.id)])
                        stcok_move_obj = self.pool.get('stock.move').browse(cr, uid,move_id )
                        for move_obj in stcok_move_obj:
                             magento_product_id = move_obj.product_id.magento_id
                             for item in order.get('items'):
                                 
                                 if item['product_id'] == str(magento_product_id) :
                                     dict1[item['item_id']] = int(move_obj.product_qty)
                                     #dict1[item['increment_id']] = str(sale_order.magento_increment_id)
                        ####End############################################################
                        try :
                            #API to create Delivery order in magneto
                            magento = server.call(session, 'sales_order_shipment.create', [sale_order.magento_increment_id, dict1, '', False, False])
                            if magento:
                               total_no_of_records+=1
                            self.pool.get('stock.picking').write(cr, uid, picking.id,{'magento_increment_id' : magento})
                        except:
                            pass
            return total_no_of_records
        except:
            return -1
    
    def export_stock(self, cr, uid,context=None):
        total_no_of_records=0 #count number of exported product's stock
        try:
            #magneto object which  connecting openerp with defined magneto configuration start
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
            if not status:
                set_export_finished()  
                return -1  
        except :
             raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password") )
            #End
        try: 
            #searching all products from openerp that exists in magneto.
            prod_ids = self.pool.get('product.product').search(cr, uid, [('magento_id', '!=', -1),('export_to_magento','=',True)])
            #making products object for all above searched products
            prods = self.pool.get('product.product').browse(cr, uid, prod_ids)
            #appending all sku code in sku_list
            sku_list = []
            for prod in prods:
                sku_list.append(prod.code)
            #API to get product stock from magneto based on sku.
            res = server.call(session, 'product_stock.list', [sku_list])
            magento_stock = {}
            for magento_prod in res:
                magento_stock[unicode(magento_prod['sku'])] = magento_prod['qty']
            if context==None:
                context={}
            for i in range(0, len(prod_ids)):
                try:
                    if context.has_key('manual_update') and context['manual_update']=='dantunes':
                        try:
                            if float(prods[i]['qty_magento']) != float(magento_stock[prods[i]['code']]):
                                entry = [prods[i]['code'], {'qty': prods[i]['qty_magento'], 'is_in_stock': 1,'manage_stock':1}]
                                #API in magneto to update stock 
                                server.call(session,'product_stock.update', entry)
                                total_no_of_records+=1 
                        except:
                            #Creating new stock entry
                            entry = [prods[i]['code'], {'qty': prods[i]['qty_magento'], 'is_in_stock': 1}]
                            #API in magneto to update stock 
                            server.call(session,'product_stock.update', entry)
                            total_no_of_records+=1 
                    else:
                        try:
                            if float(prods[i]['qty_magento']) < float(magento_stock[prods[i]['code']]):
                                entry = [prods[i]['code'], {'qty': prods[i]['qty_magento'], 'is_in_stock': 1,'manage_stock':1}]
                                #API in magneto to update stock 
                                server.call(session,'product_stock.update', entry)
                                total_no_of_records+=1 
                        except:
                            #Creating new stock entry
                            entry = [prods[i]['code'], {'qty': prods[i]['qty_magento'], 'is_in_stock': 1}]
                            #API in magneto to update stock 
                            server.call(session,'product_stock.update', entry)
                            total_no_of_records+=1
                except:
                  pass            
            return total_no_of_records
        except:
            return -1
    
    def import_stock(self, cr, uid):
        total_no_of_records=0#count number of records
        if 1== 1:
                # magneto object through which connecting openerp with defined magento configuration start
                [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
                if not status:
                    raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password") )
                    return -1 
                #searching magneto imported product in openerp 
                prod_ids = self.pool.get('product.product').search(cr, uid, [('magento_id', '!=', -1)])
                prods = self.pool.get('product.product').browse(cr, uid, prod_ids)
                sku_list = []
                for prod in prods:
                    sku_list.append(prod.code)
                res = server.call(session, 'product_stock.list', [sku_list])
                
               
                magento_stock = {}
                for magento_prod in res:
                    magento_stock[unicode(magento_prod['sku'])] = magento_prod['qty']
                magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
                location_id = magento_configuration_object[0].inital_stock_location.id
                inventry_obj = self.pool.get('stock.inventory')
                inventry_line_obj = self.pool.get('stock.inventory.line')
                name = 'Initial Magento Inventory'
                inventory_id = inventry_obj.create(cr , uid, {'name': name})
                for prod in prods:
                    try:
                        line_data ={
                            'inventory_id' : inventory_id,
                            'product_qty' : magento_stock[prod.code],
                            'location_id' : location_id,
                            'product_id' : prod.id,
                            'product_uom' : prod.uom_id.id,
                        }
                        inventry_line_obj.create(cr , uid, line_data)
                        if int(magento_stock[prod.code])>0.0:
                           total_no_of_records+=1
                    except:
                        pass
                    inventry_obj.action_confirm(cr, uid, [inventory_id])
                    inventry_obj.action_done(cr, uid, [inventory_id])
                return total_no_of_records
#        except:
#                return -1

magento_configuration()   
#configuration of picking  based on magneto
class stock_picking_out(osv.osv):
    _inherit = "stock.picking.out"
    _columns = {
        'magento_increment_id' : fields.char('Magento Increment ID',size=64),
        'export_to_magento': fields.boolean('Export to Magento'),   
    }
    _defaults = {
        
        'export_to_magento': lambda *a: False,
    } 
    
stock_picking_out()    