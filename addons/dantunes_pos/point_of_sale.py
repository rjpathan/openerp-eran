# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import logging
import pdb
import time

import openerp
from openerp import netsvc, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
import openerp.addons.product.product

_logger = logging.getLogger(__name__)

class sale_shop(osv.osv):
    _inherit="sale.shop"
    
    _columns={
                'pos_categ_id': fields.many2one('pos.category', 'Pos Category', required=True),
                'pos_recipt_footer':fields.text("POS Footer"),
              }
sale_shop()    
class pos_category(osv.osv):
    _inherit="pos.category"
    
    _columns={
              'shop_id': fields.many2one('sale.shop', 'Shop', required=True),
              'shop_ids':fields.many2many('sale.shop','shop_category_rel','shop_id','name',"Shops")
              }
    def write(self,cr,uid,ids,vals,context=None):
        if 'shop_ids' in vals:
            values = {'shop_ids':vals['shop_ids']}
            parent =self.browse(cr,uid,ids)[0].parent_id and [self.browse(cr,uid,ids)[0].parent_id.id]
            if parent:
                self.write(cr,uid,parent,values)
        res = super(pos_category,self).write(cr,uid,ids,vals,context)
        return res
    def search(self, cr, uid, args, offset=0, limit=None, order=None,context=None, count=False):
        """Override this function to return products ids which are having qty to point of sale"""
        resultpos=[]
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        if user_obj.pos_config:
                 shop=user_obj.pos_config.shop_id.id
                 args.append(('shop_ids','in',[shop]))
        res =  super(pos_category, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,context=context, count=count)
        return res
pos_category()   
    
class pos_order(osv.osv):
    _inherit="pos.order"

    def refund(self, cr, uid, ids, context=None):
        """Create a copy of order  for refund order"""
        clone_list = []
        
        
        line_obj = self.pool.get('pos.order.line')
        for order in self.browse(cr, uid, ids, context=context):
    	    curr_sess_ids=self.pool.get('pos.session').search(cr,uid,[('config_id.shop_id','=',order.shop_id.id),('state','=','opened')])
    	    if not curr_sess_ids:
                raise osv.except_osv(_('Warning !'),_(_('Bitte öffne eine Sitzung mit dem Shop ')+order.shop_id.name))
    	    name=order.name + ' REFUND'
            
            clone_id = self.copy(cr, uid, order.id, {   ###added picking_id################
                'name':name,'session_id':curr_sess_ids[0],'date_order':time.strftime('%Y-%m-%d %H:%M:%S'),'redeem_date':None,'return':True,#'picking_id':order.picking_id.id,
            }, context=context)
            clone_list.append(clone_id)

        for clone in self.browse(cr, uid, clone_list, context=context):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {
                    'qty': -order_line.qty,
                    'return_pro':True
                }, context=context)
                
        new_order = ','.join(map(str,clone_list))
        try:
            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'dantunes_pos', 'view_pos_pos_form_inherit_kt')
        except:
            view_id=False
        
        
        abs = {
            #'domain': "[('id', 'in', ["+new_order+"])]",
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':clone_list[0],
            'view_id': view_id,
            'context':context,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        return abs
    
    def _get_credit(self,cr,uid,ids, field_name, arg, context=None):
        result = {}
        for order in self.browse(cr, uid, ids, context=context):
            result[order.id] = True
            parent_id=sorted(self.search(cr,uid,[('pos_reference','=',order.pos_reference)]))[0]
            if parent_id!=order.id:
                parent_obj=self.browse(cr,uid,parent_id)
                d1=datetime.now()
                d2=datetime.strptime(parent_obj.date_order,"%Y-%m-%d %H:%M:%S")
                if (d1-d2).days>=14:
                    result[order.id] = False
        return result

    def create_credit_memo(self,cr,uid,ids,context=None):
    	credit_journal=self.pool.get('account.journal').search(cr,uid,[('code','ilike','cmemo')])
    	if not credit_journal:
    	     raise osv.except_osv(_('Warning!'),_('Please create a Journal for Credit Memo with code \'CMEMO\''))
    	vals={}
    	context['active_model']='pos.order'
    	context['active_id']=ids[0]
        obj=self.browse(cr,uid,ids[0])
        order_id=sorted(self.search(cr,uid,[('pos_reference','=',obj.pos_reference)]))[0]
        order_obj=self.browse(cr,uid,order_id)
        self.write(cr,uid,ids[0],{'pos_reference':obj.pos_reference+str(order_obj.next_no)})
        self.write(cr,uid,[order_obj.id],{'next_no':order_obj.next_no+1})
    	vals['journal_id']=credit_journal[0]
    	credit_note=self.pool.get('pos.make.payment').create(cr,uid,vals,context)
    	res=self.pool.get('pos.make.payment').check(cr,uid,[credit_note],context)
    	return res
 
    def pay_gift_card(self,cr,uid,ids,context=None):
        if context==None:
            context={}
        gift_journal=self.pool.get('account.journal').search(cr,uid,[('code','ilike','gcpay')])
        if not gift_journal:
             raise osv.except_osv(_('Warning!'),_('Please create a Journal for Gift Card Payment with code \'GCPay\' and type as Bank and checks.'))
        vals={}
        context['active_model']='pos.order'
        context['active_id']=ids[0]
        order_obj=self.browse(cr,uid,ids[0])
        self.write(cr,uid,ids[0],{'pos_reference':order_obj.pos_reference+str(order_obj.next_no)})
        self.write(cr,uid,[order_obj.id],{'next_no':order_obj.next_no+1})
        vals['journal_id']=gift_journal[0]
        gift_card=self.pool.get('pos.make.payment').create(cr,uid,vals,context)
        res=self.pool.get('pos.make.payment').check(cr,uid,[gift_card],context)
        return res
 
    def get_reference_amount(self, cr, uid,orders,reference, context=None):
        amount=0.0
        reference=reference[0]
        if reference[0]=='credit_note':
            note_ids=self.pool.get('account.move').search(cr,uid,[('pos_reference','=',reference[1]),('credit_note','=',True)])
            if not note_ids:
                raise osv.except_osv(_('Warning!'),_('Bitte einen gültigen Gutschrift Code eingeben.'))
                return False
            note_obj=self.pool.get('account.move').browse(cr,uid,note_ids[0])
            if note_obj.closed:
                raise osv.except_osv(_('Warning!'),_('Der eingegebene Gutschrift Code wurde bereits verwendet.'))
            for line in note_obj.line_id:
                if line.debit!=0:
                    amount=line.debit
                    break
            return [amount,note_obj.id,reference[1]]
        elif reference[0]=='gift_card':
            order_id=0
            order_ids=self.pool.get('pos.order').search(cr,uid,[('pos_reference','=','Order '+reference[1]),('gift_card','=',True)])
            if not order_ids:
                raise osv.except_osv(_('Warning!'),_('Bitte einen gültigen Geschenk Code eingeben.'))
                return False
            order_objs=self.pool.get('pos.order').browse(cr,uid,order_ids)
            for order_obj in order_objs:
                if order_obj.amount_total>0.0:
                    if order_obj.closed:
                        raise osv.except_osv(_('Warning!'),_('Der eingegebene Geschenk Code wurde bereits verwendet.'))
                    else:
                        amount=order_obj.amount_total
                        order_id=order_obj.id
            return [amount,order_id,reference[1]]
        

    def validate_payment_lines(self,cr,uid,temp,paylines,context=None):
    	memo_ref=[]
        giftcard_ref=[]
    	for payment in paylines:
                    if payment['type']=='credit_note':
                        memo_obj=self.pool.get('account.move').browse(cr,uid,payment['pos_reference'])
                        for line in memo_obj.line_id:
                            if line.debit!=0:
                                amount=line.debit
                                break
                        if amount!=payment['amount']:
                            raise osv.except_osv(_('Warning !'),_('Der Gutschriftbetrag in Bezug auf '+str(memo_obj.pos_reference)+' wurde von '+str(amount)+' auf '+str(payment['amount'])+' geändert.'))
                        if payment['pos_reference'] in memo_ref:
                            raise osv.except_osv(_('Warning !'),_('Gutschrift mit Bezug '+str(memo_obj.pos_reference)+' wird mehr als einmal verwendet.'))
                        memo_ref.append(payment['pos_reference'])
                    if payment['type']=='gift_card':
                        card_obj=self.pool.get('pos.order').browse(cr,uid,payment['pos_reference'])
                        amount=card_obj.amount_total
                        if amount!=payment['amount']:
                            raise osv.except_osv(_('Warning !'),_('Betrag der Geschenk-Karte mit Bezug auf '+str(card_obj.pos_reference[6:])+' wird von '+str(amount)+' auf '+str(payment['amount'])+' geändert.'))
                        if payment['pos_reference'] in giftcard_ref:
                            raise osv.except_osv(_('Warning !'),_('Geschenk-Karte mit Referenz '+str(card_obj.pos_reference[6:])+' wird mehr als einmal verwendet.'))
                        giftcard_ref.append(payment['pos_reference'])
    	return True
    
    def _is_gift_card(self,cr,uid,ids,field,args,context=None):
        res={}
        for id in ids:
            res[id]=False
            obj=self.browse(cr,uid,id)
            if obj.sale_journal and obj.sale_journal.code.lower()=='gcard' and obj.amount_total>0.0:
                res[id]=True
        return res
    
    def refund_taxes(self,cr,uid,ids,context=None):
        order=self.browse(cr,uid,ids[0])
        abs=True
        if order.amount_tax>0.0:
            curr_sess_ids=self.pool.get('pos.session').search(cr,uid,[('config_id.shop_id','=',order.shop_id.id),('state','=','opened')])
            if not curr_sess_ids:
                raise osv.except_osv(_('Warning !'),_(_('Bitte öffne eine Sitzung mit dem Shop ')+order.shop_id.name))
            product_id=self.pool.get('product.product').search(cr,uid,[('default_code','ilike','R3tt@xswitz')])
            if product_id:
                product_id=product_id[0]
            else:
                product_id=sorted(self.pool.get('product.product').search(cr,uid,[('type','=','service')]))
                product_id=product_id[0]
            res_id = self.copy(cr, uid, order.id, {
                'session_id':curr_sess_ids[0],'date_order':time.strftime('%Y-%m-%d %H:%M:%S'),'redeem_date':None,'return':True,
                'lines':[(0,0,{'product_id':product_id,'qty':1.0,'price_unit':-order.amount_tax})]
            }, context=context)
        
            abs = {
                'name': _('Return Taxes'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pos.order',
                'res_id':res_id,
                'view_id': False,
                'context':context,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
            }
        return abs
    
    _columns={
             'credit_valid':fields.function(_get_credit,type="boolean",string="Credit Valid"),
	         'next_no':fields.integer('Next Number'),		      
             'closed':fields.boolean('Closed'),
             'redeem_date':fields.date('Redeemed Date'),
             'gift_card':fields.function(_is_gift_card,string="Is Gift Card",type="boolean",store=True),
	         'return':fields.boolean('Is Return'),
             }
    _defaults={
		'next_no':1,
       	'closed':True,
		'return':False,
		}
    
pos_order()
###################################added############################################
#===============================================================================
# this is for add scrap button in the orderline of POS
#===============================================================================

class pos_order_line(osv.osv):
    
    _inherit = "pos.order.line"
    
    def _visible(self,cr,uid,ids,field_name, arg,context=None):
        result = {}
        for id in self.browse(cr,uid,ids,context):
            result[id.id] = True
            if id.qty < 0 and -(id.qty)!= id.qty_moved and id.pay:
                result[id.id] = False
        return result
    
    def _product_stock(self,cr,uid,ids,field_name,arg,context=None):
        result={}
        for obj in self.browse(cr,uid,ids,context):
	    result[obj.id] = 0
	    if obj.pay:
		    result[obj.id] = abs(obj.qty)
		    if obj.qty_moved:
			result[obj.id]=abs(obj.qty+obj.qty_moved)
        return result
    
    _columns = {
                'qty_moved':fields.integer('Scrapped'),
                'return_pro':fields.boolean('Return Products'),
                'in_visible_button':fields.function(_visible,type='boolean',string="Button In Visible"),
                'pay':fields.boolean('Paid'),
                'qty_stocked':fields.function(_product_stock,type='integer',string="Product Stocked")
                }
    
    
    _defaults = {
                 'return_pro':False,
                 'pay':False,
                 }
    
    def launch_scrap(self,cr,uid,ids,context=None):
        return{
                'name': _('Scrap Products'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pos.scrap.move',
                'view_id': False,
                'context':context,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
               }
    
    def launch_stock(self,cr,uid,ids,context=None):
        return{
                'name': _('Stock Products'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pos.scrap.move',
                'view_id': False,
                'context':context,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
               }
pos_order_line()
    
#class scrap_move_wizard(osv.):   




class pos_scrap_move(osv.osv_memory):
    
    _name = "pos.scrap.move"
    
    _columns = {
                'qty':fields.integer("Quantity"),
                
                }
    
    _defaults = {
                'qty':lambda *a:1,
                }
    
    
    def create_action_move(self,cr,uid,ids,context=None):
        if context.has_key('active_id') and context['active_id']:
            pos_order_line_obj  = self.pool.get('pos.order.line').browse(cr,uid,context['active_id'],context)
            if pos_order_line_obj:
                if context['qty']==0:
                    raise osv.except_osv( _('Warning!'), _(" %s  Quantity should be greater than Zero"%pos_order_line_obj.product_id.name))
                if context.has_key('move_to_stock') and context['move_to_stock']==1:
                    if pos_order_line_obj.qty_moved < context['qty']:
                        raise osv.except_osv( _('Warning!'), _("Cannot return quantity to stock more than the scrapped quantity"))
                else:
                    if not -(pos_order_line_obj.qty) >= context['qty']  or pos_order_line_obj.qty_moved+context['qty'] > -(pos_order_line_obj.qty):
                        raise osv.except_osv( _('Warning!'), _("Scrapped quantity should not be more than product quantity "))
                pos_order_obj = self.pool.get('pos.order').browse(cr,uid,pos_order_line_obj.order_id.id,context)
                stock_picking_obj = self.pool.get('stock.picking').browse(cr,uid,pos_order_obj.picking_id.id)
                if stock_picking_obj:
                  move_lines = stock_picking_obj.move_lines
                  if move_lines:
                      source_loc_id = move_lines[0].location_dest_id.id
                      scrap_loc=self.pool.get('stock.location').search(cr,uid,[('scrap_location','=',True)])
                      dest_loc_id = scrap_loc[0] 
                      pro_id = pos_order_line_obj.product_id.id
                      name = pos_order_line_obj.product_id.name
                      origin = pos_order_obj.name
                      qty = context['qty']
                      if context.has_key('move_to_stock') and context['move_to_stock']==1:
                          temp=source_loc_id
                          source_loc_id=dest_loc_id
                          dest_loc_id=temp
                      vals = {'name':name,'location_id':source_loc_id,'location_dest_id':dest_loc_id,'product_id':pro_id,'product_qty':qty,'product_uom':1}
                      stock_move_id = self.pool.get('stock.move').create(cr,uid,vals)
                      self.pool.get('stock.move').action_done(cr, uid, [stock_move_id], context=context)
                      if context.has_key('move_to_scrap') and context['move_to_scrap']==1:
                          self.pool.get('pos.order.line').write(cr, uid, [context['active_id']], {
                            'qty_moved':pos_order_line_obj.qty_moved+qty                                                                    
                         }, context=context)
                      if context.has_key('move_to_stock') and context['move_to_stock']==1:
                          self.pool.get('pos.order.line').write(cr, uid, [context['active_id']], {
                            'qty_moved':pos_order_line_obj.qty_moved-qty                                                                   
                         }, context=context)
                          
        try:
            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'dantunes_pos', 'view_pos_pos_form_inherit_kt')
        except:
            view_id=False
        
        
        abs = {
            #'domain': "[('id', 'in', ["+new_order+"])]",
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':pos_order_obj.id,
            'view_id': view_id,
            'context':context,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        return abs
    
pos_scrap_move()     



class pos_make_payment(osv.osv_memory):
    _inherit = 'pos.make.payment'
    _description = 'Point of Sale Payment'
    def check(self, cr, uid, ids, context=None):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        context = context or {}
        order_obj = self.pool.get('pos.order')
        obj_partner = self.pool.get('res.partner')
        active_id = context and context.get('active_id', False)

        order = order_obj.browse(cr, uid, active_id, context=context)
        amount = order.amount_total - order.amount_paid
        data = self.read(cr, uid, ids, context=context)[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = data['journal_id'][0]

        ########################################added###########################
        if amount < 0.0:
            pos_order_line_ids  = self.pool.get('pos.order.line').search(cr,uid,[('order_id','=',order.id)])
            pos_order_line_objs = self.pool.get('pos.order.line').browse(cr,uid,pos_order_line_ids,context)
            for pos_order_line_obj in pos_order_line_objs:
                 self.pool.get('pos.order.line').write(cr, uid, [pos_order_line_obj.id], {
                    'in_visible_button':False,'pay':True
                     }, context=context)
                 
        ################################ended####################################       
	data['payment_date']=datetime.now().strftime('%Y-%m-%d') 
        if amount != 0.0:
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'pos.order', active_id, 'paid', cr)
            return {'type' : 'ir.actions.act_window_close' }

        return self.launch_payment(cr, uid, ids, context=context)



########################################end####################################
