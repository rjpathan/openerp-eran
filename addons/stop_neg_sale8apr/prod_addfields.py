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




from openerp import netsvc


from datetime import datetime, date
from lxml import etree
import time
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)





class product_product(osv.osv):
    _inherit='product.product'
    
#    def _get_product_available_func(states, what):
#        
#        def _product_available(self, cr, uid, ids, name, arg, context=None):
#            active_model_pool = self.pool.get( 'mail.thread')
#            if context is None:
#             context = {}
#            active_ids = context.get('active_ids')
#        
#            
#            res_id = active_ids 
#            mail_obj=self.pool.get('mail.message')
#            body="<p>message for product information -------.</p>"
#            subject =_("subject to  product information  ")
#            print body,"Body------------"
#            part_id=self.pool.get('res.partner').search(cr,uid,[('name','=','Administrator')])[0]
#            
#            res_id=mail_obj.create(cr,uid, {'body':body,'subject':subject,'type':'comment','res_id':part_id,'to_read':True,'partner_ids':[(4,part_id)],
#                                            'model':'res.partner'},context=context)
#
#            self.pool.get('mail.notification').create(cr,uid,{'read':False,'starred':False,'partner_id':part_id,'message_id':res_id})
##            post_vars= {'body':body,
##                        'subject':subject,
##                        'model':'res.partner',
##                        'res_id':part_id,
##                        'type':"comment"}
##            
##            active_model_pool.message_post(cr,uid,[ ],  subtype='mt_comment', context=context, **post_vars)
#           
#            print "It came here after creating------------------------------------------------"
#            
#            
#            
#            
#            return {}.fromkeys(ids, 0.0)
#        
#           
# 
#        return _product_available
#        
#    
#    _product_qty_available = _get_product_available_func(('done',), ('in', 'out'))


    
    
    _columns = {
#                'qty_available': fields.function(_product_available, type='float', string='Quantity On Hand'),
                'check_box':fields.boolean("Disable Negative Inventory")
                                          
               }
product_product()     



class sale_order(osv.osv):
    _inherit="sale.order"
    
    
    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sales order to which the order lines belong
        :param list(browse_record) order_lines: sales order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if ommitted.
        :return: True
        """
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []
        prod_obj=self.pool.get("product.product")
        
        dic={} 
        print 'sale.order is calling--------------'
        for lin in order_lines:
                     
                     if lin.product_id.check_box:
                       if lin.product_uom_qty>lin.product_id.qty_available:
                              q=lin.product_uom_qty-lin.product_id.qty_available
                       
                        
                       if lin.product_id.qty_available<0:
                        raise osv.except_osv(_('Warning!'), _('Physical inventory is in Negative for the product %s  ')% (lin.product_id.name))
                       if lin.product_id.qty_available==0  :
                        raise osv.except_osv(_('Warning!'), _('Physical inventory is zero for the product %s  ')% (lin.product_id.name))
                       
                        
                       if lin.product_id.qty_available<lin.product_uom_qty:
                        
                            raise osv.except_osv(_('Warning!'), _(' %s ordered quantity is greater than Current Stock .Current stock is :%s .Please change the ordered quantity !') % (lin.product_id.name,lin.product_id.qty_available))
        
                       if dic.has_key(lin.product_id.id):
                            if lin.product_uom_qty>dic[lin.product_id.id]:
                               raise osv.except_osv(_('Warning!'), _(' %s ordered quantity is greater than Current Stock .Current stock is :%s .Please change the ordered quantity !') % (lin.product_id.name,lin.product_id.qty_available))
                            else:
                                 dic[lin.product_id.id]-=lin.product_uom_qty
                       else:
                            dic[lin.product_id.id]=lin.product_id.qty_available-lin.product_uom_qty
        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)
           
            if line.product_id:
                if line.product_id.type in ('product', 'consu'):
                    
                     if not picking_id:
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                   
                    
                    
                    
                     move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context))
                else:
                    # a service has no stock move
                    move_id = False
                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context))
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")
        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True
    
    def action_ship_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            self._create_pickings_and_procurements(cr, uid, order, order.order_line, None, context=context)
        return True
    
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id
        
        
        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            #'state': 'waiting',
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0
            }
    
    
    
sale_order()    
    
    
# This method will call when we deliver any product    
    
    
class invoice_directly(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    def do_partial(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time.'
        stock_picking = self.pool.get('stock.picking')
        stock_move = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        prod_obj=self.pool.get("product.product")
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        
        dic={}
        for lin in partial.move_ids:
                
             if lin.product_id.check_box:
               if lin.product_id.qty_available<0:
                 raise osv.except_osv(_('Warning!'), _('physical inventory is in negative '))
               if lin.product_id.qty_available==0:
                   raise osv.except_osv(_('Warning!'), _('physical inventory is zero for the product %s') % (lin.product_id.name))
            
               if lin.quantity>lin.product_id.qty_available:
                  raise osv.except_osv(_('Warning!'), _('You cannot deliver %s!.Current stock is :%s .Please change the quantity !') % (lin.product_id.name,lin.product_id.qty_available))
               if dic.has_key(lin.product_id.id):
                  if lin.quantity>dic[lin.product_id.id]:
                     raise osv.except_osv(_('Warning!'), _('You cannot deliver %s!.Current stock is :%s .Please change the quantity !') % (lin.product_id.name,lin.product_id.qty_available))
                  else:
                      dic[lin.product_id.id]-=lin.quantity
               else:
                   dic[lin.product_id.id]=lin.product_id.qty_available-lin.quantity
               
        qty={}
        picking_type = partial.picking_id.type
        for wizard_line in partial.move_ids:
            line_uom = wizard_line.product_uom
            move_id = wizard_line.move_id.id
            #Quantiny must be Positive
            if wizard_line.quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Please provide proper Quantity.'))

            qty_in_line_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, line_uom.id)
            if line_uom.factor and line_uom.factor <> 0:
                if float_compare(qty_in_line_uom, wizard_line.quantity, precision_rounding=line_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The unit of measure rounding does not allow you to ship "%s %s", only roundings of "%s %s" is accepted by the Unit of Measure.') % (wizard_line.quantity, line_uom.name, line_uom.rounding, line_uom.name))
            if move_id:
                #Check rounding Quantity.ex.
                #picking: 1kg, uom kg rounding = 0.01 (rounding to 10g),
                #partial delivery: 253g
                #=> result= refused, as the qty left on picking would be 0.747kg and only 0.75 is accepted by the uom.
                initial_uom = wizard_line.move_id.product_uom
                #Compute the quantity for respective wizard_line in the initial uom
                qty_in_initial_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, initial_uom.id)
                without_rounding_qty = (wizard_line.quantity / line_uom.factor) * initial_uom.factor
                if float_compare(qty_in_initial_uom, without_rounding_qty, precision_rounding=initial_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The rounding of the initial uom does not allow you to ship "%s %s", as it would let a quantity of "%s %s" to ship and only roundings of "%s %s" is accepted by the uom.') % (wizard_line.quantity, line_uom.name, wizard_line.move_id.product_qty - without_rounding_qty, initial_uom.name, initial_uom.rounding, initial_uom.name))
            else:
                seq_obj_name =  'stock.picking.' + picking_type
                move_id = stock_move.create(cr,uid,{'name' : self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                    'product_id': wizard_line.product_id.id,
                                                    
                                                    'product_qty': wizard_line.quantity,
                                                    'product_uom': wizard_line.product_uom.id,
                                                    'prodlot_id': wizard_line.prodlot_id.id,
                                                    'location_id' : wizard_line.location_id.id,
                                                    'location_dest_id' : wizard_line.location_dest_id.id,
                                                    'picking_id': partial.picking_id.id
                                                    },context=context)
                stock_move.action_confirm(cr, uid, [move_id], context)
            partial_data['move%s' % (move_id)] = {
                'product_id': wizard_line.product_id.id,
                'product_qty': wizard_line.quantity,
                'product_uom': wizard_line.product_uom.id,
                'prodlot_id': wizard_line.prodlot_id.id,
            }
            if (picking_type == 'in') and (wizard_line.product_id.cost_method == 'average'):
                partial_data['move%s' % (wizard_line.move_id.id)].update(product_price=wizard_line.cost,
                                                                  product_currency=wizard_line.currency.id)
            
#        code to notify on the message wall when Inventory reaches 0.0 or negative
            l_id=wizard_line.location_id.id
            con={'location':l_id}
            required={'qty_available':0.0}
            val=self.pool.get('product.product')._product_available(cr,uid,[wizard_line.product_id.id],required,context=con)
            print val,'val--------------'            
            product=wizard_line.product_id
            if qty.has_key(product.id):
                qty[product.id]-=wizard_line.quantity
            else:
                qty[product.id]=val[wizard_line.product_id.id]['qty_available']-wizard_line.quantity
            if qty[product.id]<=0:
                mail_obj=self.pool.get('mail.message')
                body="<p> <b>%s</b> is Running Out of Stock at %s Warehouse.<br>Please Update the stock !!</p>"%(product.name,wizard_line.location_id.name)
                subject =_(" Notification on Product Inventory ")
                user_obj=self.pool.get('res.users').browse(cr,uid,uid)
                part_id=self.pool.get('res.partner').search(cr,uid,[('name','=','Administrator')])[0]
                c_part_id=self.pool.get('res.partner').search(cr,uid,[('name','=',user_obj.name)])[0]
                res_id=mail_obj.create(cr,uid, {'body':body,'subject':subject,'type':'comment','res_id':c_part_id,'to_read':True,'notified_partner_ids':[(4,part_id),(4,c_part_id)],
                                                'model':'res.partner'},context=context)
            
                self.pool.get('mail.notification').create(cr,uid,{'read':False,'starred':False,'partner_id':c_part_id,'message_id':res_id})
        stock_picking.do_partial(cr, uid, [partial.picking_id.id], partial_data, context=context)
        return {'type': 'ir.actions.act_window_close'}

invoice_directly()

# This code is for partial move 


class stock_partial_move(osv.osv_memory):
    
    
    _inherit="stock.partial.move"
    
    
    def do_partial(self, cr, uid, ids, context=None):
        # no call to super!
        
        assert len(ids) == 1, 'Partial move processing may only be done one form at a time.'
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        
        dic={}
        for lin in partial.move_ids:
                
             if lin.product_id.check_box:
               if lin.product_id.qty_available<0:
                 raise osv.except_osv(_('Warning!'), _('Stock is in negative for the product %s')% (lin.product_id.name))
               if lin.product_id.qty_available==0:
                   raise osv.except_osv(_('Warning!'), _('stock  is zero for the product %s') % (lin.product_id.name))
            
               if lin.quantity>lin.product_id.qty_available:
                  raise osv.except_osv(_('Warning!'), _('You cannot deliver %s!.Current stock is :%s .Please change the quantity !') % (lin.product_id.name,lin.product_id.qty_available))
               if dic.has_key(lin.product_id.id):
                  if lin.quantity>dic[lin.product_id.id]:
                     raise osv.except_osv(_('Warning!'), _('You cannot deliver %s!.Current stock is :%s .Please change the quantity !') % (lin.product_id.name,lin.product_id.qty_available))
                  else:
                      dic[lin.product_id.id]-=lin.quantity
               else:
                   dic[lin.product_id.id]=lin.product_id.qty_available-lin.quantity
        
        
        
        moves_ids = []
        for move in partial.move_ids:
            move_id = move.move_id.id
            partial_data['move%s' % (move_id)] = {
                'product_id': move.product_id.id,
                'product_qty': move.quantity,
                'product_uom': move.product_uom.id,
                'prodlot_id': move.prodlot_id.id,
            }
            moves_ids.append(move_id)
            if (move.move_id.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
                partial_data['move%s' % (move_id)].update(product_price=move.cost,
                                                          product_currency=move.currency.id)
        self.pool.get('stock.move').do_partial(cr, uid, moves_ids, partial_data, context=context)
        return {'type': 'ir.actions.act_window_close'}
    
stock_partial_move()
    

# This method will call when we click the button process entirely



class stock_move(osv.osv):
     _inherit="stock.move"  
    
    
     def action_done(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        @return:
        """
        picking_ids = []
        move_ids = []
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
          
        lin = self.browse(cr, uid, ids[0], context=context)
       
        dic={}
        
        if lin.product_id.check_box:
            if lin.product_id.qty_available<0:
               raise osv.except_osv(_('Warning!'), _('stock is in negative for the product %s ') % (lin.product_id.name))
            if lin.product_id.qty_available==0:
                 raise osv.except_osv(_('Warning!'), _('stock is zero for the product %s') % (lin.product_id.name))
            
            if lin.product_qty>lin.product_id.qty_available:
               raise osv.except_osv(_('Warning!'), _('You cannot deliver %s!.Current stock is :%s .Please change the quantity !') % (lin.product_id.name,lin.product_id.qty_available))
            if dic.has_key(lin.product_id.id):
                if lin.product_qty>dic[lin.product_id.id]:
                     raise osv.except_osv(_('Warning!'), _('You cannot deliver %s!.Current stock is :%s .Please change the quantity !') % (lin.product_id.name,lin.product_id.qty_available))
                else:
                      dic[lin.product_id.id]-=lin.product_qty
            else:
                   dic[lin.product_id.id]=lin.product_id.qty_available-lin.product_qty
        todo = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state=="draft":
                todo.append(move.id)
        if todo:
            self.action_confirm(cr, uid, todo, context=context)
            todo = []

        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done','cancel']:
                continue
            move_ids.append(move.id)

            if move.picking_id:
                picking_ids.append(move.picking_id.id)
            if move.move_dest_id.id and (move.state != 'done'):
                # Downstream move should only be triggered if this move is the last pending upstream move
                other_upstream_move_ids = self.search(cr, uid, [('id','!=',move.id),('state','not in',['done','cancel']),
                                            ('move_dest_id','=',move.move_dest_id.id)], context=context)
                if not other_upstream_move_ids:
                    self.write(cr, uid, [move.id], {'move_history_ids': [(4, move.move_dest_id.id)]})
                    if move.move_dest_id.state in ('waiting', 'confirmed'):
                        self.force_assign(cr, uid, [move.move_dest_id.id], context=context)
                        if move.move_dest_id.picking_id:
                            wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                        if move.move_dest_id.auto_validate:
                            self.action_done(cr, uid, [move.move_dest_id.id], context=context)

            self._create_product_valuation_moves(cr, uid, move, context=context)
            if move.state not in ('confirmed','done','assigned'):
                todo.append(move.id)

        if todo:
            self.action_confirm(cr, uid, todo, context=context)

        self.write(cr, uid, move_ids, {'state': 'done', 'date': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        for id in move_ids:
             wf_service.trg_trigger(uid, 'stock.move', id, cr)

        for pick_id in picking_ids:
            wf_service.trg_write(uid, 'stock.picking', pick_id, cr)

        return True
    

stock_move()

class sale_shop(osv.osv):
    _inherit="sale.shop"
    
    
    _columns={     
              'address_id':fields.text("Owner Address")
              }
    
   
       
    
    
sale_shop()   
    

class pos_session(osv.osv):
    
    
    _inherit="pos.session"
    
     
    def on_change_get_pos(self,cr,uid,ids,user,context=None):
           
          res_obj=self.pool.get('res.users').browse(cr,uid,user)
           
          return {'value':{'config_id': res_obj.pos_config.id }}
       
#   Code to filter POS sessions with respect to manager  
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        user_id = context.get('user_id', False) or False
        if user_id:
            user = self.pool.get('res.users').search(cr, uid,[('name','=','Administrator')], context=context)
            if user[0]!=uid:
                args = [('user_id', '=',uid)]
        return super(pos_session, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
pos_session()    
    

class pos_config(osv.osv):
    
    _inherit="pos.config"    
    
    
    _columns={
              
       'shop_id' : fields.many2one('sale.shop', 'Shop',
             required=True),
       'user_id' : fields.many2one('res.users', 'user_id' , #invisible=True                   
                                   ),
              
              
               }
    
#   Code to filter POS configurations with respect to manager  
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        print context,'context--------------'
        user_id = context.get('user_id', False) or False
        if user_id:
            user = self.pool.get('res.users').search(cr, uid,[('name','=','Administrator')], context=context)
            print user,'user-------------'
            if user[0]!=uid:
                args = [('user_id', '=',uid)]
        return super(pos_config, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

#    def on_change_get_shop(self,cr,uid,ids,arg,context=None):
#        print "YEs callling onchange =========="
#        res_obj=self.pool.get('pos.config').browse(cr,uid,arg)
#        
#        res={}
#       
#        print res_obj,"------------"   
#        print res_obj.session_ids[0].user_id.name,"User Id==============="
#        if res_obj.session_ids[0].user_id.name == "Administrator":
#                  res['readonly']=True
#      
#        return res 
#    
      
   
#    def get_user_id(self,cr,uid,context=None):
#       
#        
#       obj=self.pool.get('pos.config').browse(cr,uid,[])
#       print obj,"Which obhext============"
#       
#       sop_ids= self.pool.get('pos.config').search(self.cr,self.uid,[('shop_id.id','=',id)])
#       stk_objs= self.pool.get('pos.config').browse(self.cr,self.uid,sop_ids)
#       print stk_objs,"Object============"
##       
#       for record in stk_objs:
#        session=record.session_ids[0]
#        print session.user_id.name,"user _id========="
#              
#
#       return  session.user_id.name #obj.session_ids[0].user_id.name

    
    
    
    
    
    
    _defaults = {
      
        'user_id' : lambda self, cr, uid, context: uid,
        }
    




    
pos_config()












   
   
   