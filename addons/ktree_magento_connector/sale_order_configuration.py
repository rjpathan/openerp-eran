from osv import fields,osv
from mx import DateTime
from openerp.tools.translate import _
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

#inherit magento_configuration class to add sale import function
class magento_configuration(osv.osv):
    _inherit = 'magento.configuration'
    
    def import_orders (self,cr,uid): #Customized Import Order Function
        total_no_of_records=0# Number of sale order imported  
        start_timestamp = str(DateTime.utc())
        if True:
            # magneto object through which connecting openerp with defined magento configuration start
            start_timestamp = str(DateTime.utc())
            magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
            last_import = magento_configuration_object[0].last_imported_invoice_timestamp
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
            #checking server status
            if not status:
                raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password") )
                server.endSession(session)
                return -1
            #end
            #API to fetch all sale order information###################################################
            listorder = server.call(session, 'sales_order.list',[{'updated_at': {'from':last_import}}])
            
            all_increment_id=[]
            all_customer_id=[]
            for info_order in listorder:
                if info_order['customer_id']:
                    all_customer_id.append(info_order['customer_id'])
                all_increment_id.append(info_order['increment_id'])
            min=0
            max_number_order_import=20
            if magento_configuration_object[0].max_number_order_import:
                max_number_order_import=int(magento_configuration_object[0].max_number_order_import)
            max=max_number_order_import
            length_ord=len(listorder)
            while length_ord>0:
                all_customer_id_max=all_customer_id[min:max]
                all_increment_id_max=all_increment_id[min:max]  
#                try:
#                   #API to get customer information for all customer_id at a time 
                info_customers = [server.call(session, 'customapi_customer.itemslist' , [all_customer_id_max])][0];
#                except:
#                   info_customers=[] 
                
#                try:     
                   #API to get sale order information for all increment_ids at a time
                info_orders = [server.call(session, 'customapi_order.itemslist',[all_increment_id_max])][0]; 
#                except:
#                   info_orders=[]   
                
                min=max
                length_ord=length_ord-max_number_order_import
                if length_ord<max_number_order_import:
                    max=min+length_ord 
                else:
                    max=max+max_number_order_import 
                for info_order in info_orders: 
                        header=info_order['0']
                        #API to get sale order information based on increment_id
                        name_sales_order = str(header['increment_id'])
                        #searching sale order availability in openerp based on magneto_id or Order Reference
                        id_orders = self.pool.get('sale.order').search(cr, uid, ['|',('magento_id', '=', header['order_id']),('name', '=', name_sales_order)])
                        if True:
                            #To get customer information for each sale order from list of info_customers
                            info_customer = [customer for customer in info_customers if header['customer_id']==customer['customer_id']]
                            if info_customer:
                                info_customer=info_customer[0]
                            else:
                                info_customer = {
                                        'customer_id' : '0'
                                    }
                            pricelist_ids = self.pool.get('product.pricelist').search(cr, uid,[])
                            if (header['customer_is_guest'] == '1'):
                                info_customer['store_id'] = header['store_id']
                                info_customer['website_id'] = '1'
                                info_customer['email'] = header['customer_email']
                                info_customer['firstname'] = info_order['billing_address']['firstname']
                                info_customer['lastname'] = info_order['billing_address']['lastname']
                                info_customer['customer_is_guest'] = '1'
                            info_customer['shipping_address'] = info_order['shipping_address']
                            info_customer['billing_address'] = info_order['billing_address']
                            #getting billing and shipping address id from openerp
                            erp_customer_info = self.pool.get('magento.configuration').update_customer(cr, uid, info_customer)
                        if id_orders == []:     
                            if  header['status'] == 'canceled':
                                state = 'cancel'
                            else:
                                state = 'draft'    
                            erp_sales_order = {
                                            'name' : name_sales_order,
                                            'order_policy' : 'manual',  
                                            'state' : state,  
                                            'partner_id' : erp_customer_info['id'],
                                            'partner_invoice_id'  : erp_customer_info['billing_id'],
                                            'partner_order_id'    : erp_customer_info['billing_id'],
                                            'partner_shipping_id' : erp_customer_info['shipping_id'],
                                            'pricelist_id'        : pricelist_ids[0],
                                            'magento_id'      : header['order_id'],
                                            'magento_increment_id' : header['increment_id'],
                                            'order_policy':'prepaid',
                                           }
                            #===================================================
                            # To Add Magento Order Date to OpenERP sale Order
                            #===================================================
                            if header.has_key('created_at') and header['created_at']:
                                try:
                                    o_date=datetime.datetime.strptime(header['created_at'],'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                                    erp_sales_order['date_order']=o_date
                                except:
                                    pass
                            
                            
                            #creating sale order record in openerp
                            #===================================================
                            # To Store the payment method information i openerp from magento
                            #===================================================
                            if 'method' in  info_order['payment'].keys() and (info_order['payment']['method']):
                                          erp_sales_order[ 'payment_method_string']=info_order['payment']['method']
                                          payment=erp_sales_order[ 'payment_method_string']
                                          if payment and payment.lower() in ['ops_paysafecard','ops_cc']:
                                                journal = self.pool.get('account.journal').search(cr,uid,[('name','ilike','Kartenzahlungen Webshop')])
                                          elif payment and payment.lower() =='bankpayment':      
                                                journal = self.pool.get('account.journal').search(cr,uid,[('name','ilike','vorkasse')])
                                          elif payment and 'paypal' in payment.lower():
                                                journal = self.pool.get('account.journal').search(cr,uid,[('name','ilike','Paypal')])    
                                          elif payment and 'sofort' in payment.lower():
                                                journal = self.pool.get('account.journal').search(cr,uid,[('name','ilike','Sofort')])           
                                          else:
                                                journal = False 
                                          if journal:
                                              erp_sales_order[ 'payment_me']=journal[0]
                            #=====================================
                            # End
                            #=====================================
                            id_orders = [self.pool.get('sale.order').create(cr, uid, erp_sales_order)]
                            if id_orders:
                               total_no_of_records+=1 
                            missing_products_in_openerp=False
                            parents = {}
                            product_ids_shop = []
                            base_price=0.0
                            #fetching sale order line information from magneto 
                            
                            for item in info_order['items']:	
                                if item.has_key('product_type') and (item['product_type'] == 'configurable'):
                                    parents[item['item_id']] = {
                                        'base_price':   item['base_price_incl_tax'],
                                        'tax_percent':  item['tax_percent'],
                                        'discount_amount':float(item['discount_amount']),
                                        'discount_percent':float(item['discount_percent']),
                                    }
                                    continue
                                #searching product availability in openerp for each sale order line
                                product_ids = self.pool.get('product.product').search(cr, uid, [('magento_id', '=', item['product_id'])])
                                if (product_ids == []):
                                    try:
                                       info_products = server.call(session, 'customapi_product.itemslist',[item['product_id']])
                                    except:
                                       info_products=[] 
                                    missing_products_in_openerp = True
                                    continue
                                product_id = product_ids[0]
                                if base_price:
                                    price =  base_price                                    
                                else:
                                    price = item['base_price_incl_tax']
                                if not price and item['parent_item_id']:
                                    price = parents[item['parent_item_id']]['base_price']    
                                if  item.has_key('product_type') and (item['product_type'] != 'simple'):
                                       price=0.0    
                                #making product object for each sale order line's product
                                my_product = self.pool.get('product.product').browse(cr, uid, product_id)  
                                #===============================================
                                # For shop selection
                                #===============================================
                                pos_categ  = my_product.pos_categ_id
                                if  pos_categ and pos_categ.shop_ids:
                                        for shop in pos_categ.shop_ids:
                                             product_ids_shop.append(shop.id)
                               #=======================================
                               # End
                               #=======================================
                               
                               #================================================
                               # To Sync Discount and Discount amount
                               #============================i====================
                                discount_amount=float(item['discount_amount'])
                                if float(item['discount_amount']):
                                    	discount_amount=float(item['discount_amount'])
                                else:
                                    if parents.has_key(item['parent_item_id']):
                                         discount_amount=parents[item['parent_item_id']]['discount_amount']
                                dis_percentage=float(item['discount_percent'])
                                if float(item['discount_percent']):
                                        dis_percentage=float(item['discount_percent'])
                                else:
                                    if parents.has_key(item['parent_item_id']):
                                        dis_percentage=parents[item['parent_item_id']]['discount_percent']
                               #================================================
                               # End
                               #================================================
                                
                                if item['tax_percent']=='0.0000' and item['parent_item_id']:
                                    try:
                                         item['tax_percent']=parents[item['parent_item_id']]['tax_percent']
                                    except:
                                              item['tax_percent']='0.0000'
                                try:
                                    if (item['tax_percent'] != '0.0000'):
                                        tax_id = self.pool.get('magento.configuration').get_tax_id(cr, uid, item['tax_percent'])
                                        if (tax_id == 0):
                                            raise 
                                        else:
                                            tax_ids = [[6,0,[tax_id]]]   
                                    else:
                                        tax_ids = []
                                except:
                                    tax_ids = []      
                                erp_sales_order_line = { 'order_id'      : id_orders[0],
                                                         'product_id'      : product_id,
                                                         'name'            : item['name'],
                                                         'tax_id'          : tax_ids,
                                                         'price_unit'      : price,
                                                         'product_uom'     : my_product['uom_id']['id'],
                                                         'product_uom_qty' : item['qty_ordered'],
                                                         'discount'        : dis_percentage,
                                                         'discount_amount' : discount_amount and discount_amount-0.01 or 0.00,
                                }
                                #creating sale order line record in openerp
                                id_order_line = self.pool.get('sale.order.line').create(cr, uid, erp_sales_order_line)
###                                for shop checking in pos and storing in sale order
                            if product_ids_shop:
                                 list1 = list(set(product_ids_shop))
                                 if len(list1)==1:
                                     self.pool.get('sale.order').write(cr,uid,[id_orders[0]],{'shop_id':list1[0]})
                            #Shipping costs
                            try:
                                my_shipping = magento_configuration_object[0].shipping_product.id
                                try:
                                    if (header['shipping_tax_amount'] != '0.0000'):
                                        tax_percent = 100 * float(header['shipping_tax_amount']) / float(header['shipping_amount'])
                                        tax_id = self.pool.get('magento.configuration').get_tax_id(cr, uid, tax_percent)
                                        if (tax_id == 0):
                                            raise  
                                        else:
                                            tax_ids = [[6,0,[tax_id]]]      
                                    else:
                                        tax_ids = []     
                                except:
                                    tax_ids = []
                                if (header['shipping_incl_tax'] !='0.0000'):
                                          erp_ship_line = {
                                                         'order_id'      : id_orders[0],
                                                         'name'            : header['shipping_description'].replace('Select Shipping Method','Shipping Charges'),
                                                          'price_unit'      : float(header['base_shipping_incl_tax']),
                                                          'product_id' :my_shipping,
                                                          'tax_id':tax_ids,
                                                          'product_uom_qty' : 1,
                                                        }
                                          order_line = self.pool.get('sale.order.line').create(cr, uid, erp_ship_line)        
                            except:
                                pass
                            if missing_products_in_openerp:
                                continue 
                        else:
                           pass
            #updating last imported time in openerp magneto object
            if magento_configuration_object[0].id:
                self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'last_imported_invoice_timestamp':start_timestamp})    
                server.endSession(session)
                return total_no_of_records    
        server.endSession(session)
        return -1  
    
magento_configuration()    
#Sale orders Configuration based on magneto syn
class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    _columns = {
        'magento_id' : fields.integer('Magento ID'),
        'magento_increment_id' :fields.char('Magento Increment ID',size =64),  
        'payment_method_string':fields.char('Payment method at magento'),
        'payment_me':fields.many2one('account.journal','Payment method')
    }
    #creating index for search records
    def _auto_init(self, cr, context=None):
        super(sale_order, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'sale_magneto_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_magneto_id ON sale_order (magento_id)')
sale_order()

#===============================================================================
# This Code to Map Payment method of magento at invoice level while payment 
#===============================================================================
class invoice(osv.osv):
    _inherit = 'account.invoice'

    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
        journal = False
        inv = self.browse(cr, uid, ids[0], context=context)
        if inv.type=="out_invoice":
             sale_order = self.pool.get('sale.order')
             sale_ids = sale_order.search(cr,uid,[('name','=',inv.origin)])
             sale_obj = sale_order.browse(cr,uid,sale_ids)
             if sale_obj and sale_obj[0].payment_me:
                 journal = sale_obj[0].payment_me.id
        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'default_partner_id': self._find_partner(inv).id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'default_reference': inv.name,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'journal_id':journal,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }

invoice()


class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        if not journal_id:
            res={}
            res['value']={}
            if 'journal_id' in context.keys():
                    res['value']['journal_id'] = context['journal_id']
            return res
        
        res = self.recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
        vals = self.recompute_payment_rate(cr, uid, ids, res, currency_id, date, ttype, journal_id, amount, context=context)
        for key in vals.keys():
            res[key].update(vals[key])
        #TODO: onchange_partner_id() should not returns [pre_line, line_dr_ids, payment_rate...] for type sale, and not 
        # [pre_line, line_cr_ids, payment_rate...] for type purchase.
        # We should definitively split account.voucher object in two and make distinct on_change functions. In the 
        # meanwhile, bellow lines must be there because the fields aren't present in the view, what crashes if the 
        # onchange returns a value for them
        if ttype == 'sale':
            del(res['value']['line_dr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        elif ttype == 'purchase':
            del(res['value']['line_cr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        return res
    
account_voucher()    
#===============================================================================
# End
#===============================================================================
#===============================================================================
# Discount amount at Sale order Line
#===============================================================================

class sale_order_line(osv.osv):
    _inherit="sale.order.line"
    
    _columns={
              'discount_amount':fields.float('Discount Amount')
              }
    
    def onchange_discount(self,cr,uid,ids,price_unit,discount,dis_amount):
        if discount:
            dis_amount=round(price_unit*discount/100,2)
        elif dis_amount:
            discount=round(dis_amount*100.0/price_unit,2)
        return {'value':{'discount':discount,'discount_amount':dis_amount}}
    
sale_order_line()

#===============================================================================
# End
#===============================================================================
