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

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
                'magento_creditmemo_id':fields.integer("Magento Credit memo id",size=250)
                }
class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
                'magento_creditmemo_id':fields.integer("Magento Credit memo id",size=250)
                }    
    
    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,invoice_vals, context=None):
        result=super(stock_picking,self)._prepare_invoice_line(cr,uid,group, picking, move_line, invoice_id,invoice_vals, context)
        result['stock_update']=move_line.stock_update
        result['move_id']=move_line.id
        return result
    
    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.invoice_state != '2binvoiced':
                continue
            partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner !'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))

            if not inv_type:
                inv_type = self._get_invoice_type(picking)
            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                invoice_id, invoice_vals, context=context)
                if vals:
                    invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                    self._invoice_line_hook(cr, uid, move_line, invoice_line_id)

            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'invoice_state': 'invoiced',
                }, context=context)
            self._invoice_hook(cr, uid, picking, invoice_id)
            if picking.magento_creditmemo_id:
                 invoice_obj.write(cr,uid,[invoice_id],{'magento_creditmemo_id':picking.magento_creditmemo_id})
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
            }, context=context)
        return res

class stock_return_picking(osv.osv):
    _inherit = 'stock.return.picking'
    
    def create_returns_from_magento(self, cr, uid, ids, products,return_to_stock,creditmemo,context=None):
        """ 
         Creates return picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {} 
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.memory')
        act_obj = self.pool.get('ir.actions.act_window')
        model_obj = self.pool.get('ir.model.data')
        wf_service = netsvc.LocalService("workflow")
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0], context=context)
        date_cur = time.strftime('%Y-%m-%d %H:%M:%S')
        set_invoice_state_to_none = True
        returned_lines = 0
        
        location = self.pool.get('stock.location').search(cr,uid,[('name','=','Scrap')])
#        Create new picking for returned products
        if pick.type =='out':
            new_type = 'in'
        elif pick.type =='in':
            new_type = 'out'
        else:
            new_type = 'internal'
        seq_obj_name = 'stock.picking.' + new_type
        new_pick_name = self.pool.get('ir.sequence').get(cr, uid, seq_obj_name)
        new_picking = pick_obj.copy(cr, uid, pick.id, {
#                                        'name': _('%s-%s-return') % (new_pick_name, pick.name),
                                        'name':context['increment_id'],
                                        'move_lines': [], 
                                        'state':'draft', 
                                        'type': new_type,
                                        'date':date_cur, 
                                        'invoice_state': '2binvoiced',
                                        'magento_creditmemo_id':creditmemo['creditmemo_id']
        })
        
        val_id = data['product_return_moves']
        for v in val_id:
            data_get = data_obj.browse(cr, uid, v, context=context)
            mov_id = data_get.move_id.id
            if str(data_get.product_id.magento_id) not in products.keys():
                continue
            new_qty = products[str(data_get.product_id.magento_id)]
            update_inventory = int(return_to_stock[str(data_get.product_id.magento_id)])
            move = move_obj.browse(cr, uid, mov_id, context=context)
            new_location = move.location_dest_id.id
            returned_qty = move.product_qty
            for rec in move.move_history_ids2:
                returned_qty -= rec.product_qty

            if returned_qty != new_qty:
                set_invoice_state_to_none = False
            if new_qty:
                returned_lines += 1
                new_move=move_obj.copy(cr, uid, move.id, {
                                            'product_qty': new_qty,
                                            'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                                            'picking_id': new_picking, 
                                            'state': 'draft',
                                            'location_id': new_location, 
                                            'location_dest_id': move.location_id.id,
                                            'date': date_cur,
                                            'magento_increment_id':creditmemo['increment_id']
                })
                if update_inventory:
                    move_obj.write(cr,uid,[new_move],{'stock_update':True})
                else:
                    move_obj.write(cr,uid,[new_move],{'location_dest_id':location[0]})
                move_obj.write(cr, uid, [move.id], {'move_history_ids2':[(4,new_move)]}, context=context)
#===============================================================================
#        if creditmemo['base_shipping_tax_amount'] and creditmemo['base_shipping_amount']:
#                                      product_id = magento_configuration_object[0].shipping_product.id
#                                      product_obj = magento_configuration_object[0].shipping_product.name
#                                      a_m_l = {}
#                                      a_m_l['origin']=sale_obj.name
#                                      a_m_l['product_id']=product_id
#                                      a_m_l['name']=product_obj
#                                      a_m_l[ 'picking_id']= new_picking, 
#                                      a_m_l['invoice_id']=refund_inv_id
#                                      a_m_l['price_unit']=creditmemo['base_shipping_amount']
#                                      a_m_l['partner_id']=customer_id
#                                      try:
#                                         tax_percent = float(creditmemo['base_shipping_tax_amount'])/float(creditmemo['base_shipping_amount'])*100
#                                         tax_id = self.pool.get('magento.configuration').get_tax_id(cr, uid, tax_percent)
#                                         a_m_l['invoice_line_tax_id']=[[6,0,[tax_id]]]
#                                      except:
#                                             pass
#                                      self.pool.get('stock.move').create(cr,uid,a_m_l)
#===============================================================================
        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))
        if 'magento' in context.keys():
            name =context['magento']
            pick_obj.write(cr, uid, [pick.id], {'origin':name,}, context=context)
        if set_invoice_state_to_none:
            pick_obj.write(cr, uid, [pick.id], {'invoice_state':'none',}, context=context)
        wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
        pick_obj.force_assign(cr, uid, [new_picking], context)
        context2={
            'active_model': 'stock.picking.in',
            'active_ids': [new_picking],
            'active_id': len([new_picking]) and [new_picking][0] or False
        }
        stock_pp=self.pool.get('stock.partial.picking').create(cr,uid,{'picking_id':new_picking},context2)
        self.pool.get('stock.partial.picking').do_partial(cr,uid,[stock_pp],{})
        journal = self.pool.get('account.journal').search(cr,uid,[('type','=','sale_refund')])
        sio = self.pool.get('stock.invoice.onshipping').create(cr,uid,{'jouranl_id':journal[0]},context2)
        result = self.pool.get('stock.invoice.onshipping').open_invoice(cr,uid,[sio],context2)
        model_list = {
                'out': 'stock.picking.out',
                'in': 'stock.picking.in',
                'internal': 'stock.picking',
        }
        return result

stock_return_picking()

#inherit magento_configuration class to add partner import and export functions
class magento_configuration(osv.osv):
    _inherit = 'magento.configuration'
  
    
    def import_credit_memos(self,cr,uid): #Customized Import creditmemo Function
        total_no_of_records=0# Number of credit memos imported  
        start_timestamp = str(DateTime.utc())
        if True:
            # magneto object through which connecting openerp with defined magento configuration start
            start_timestamp = str(DateTime.utc())
            magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
            last_import = magento_configuration_object[0].last_imported_credit_timestamp
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
            #checking server status
            if not status:
                raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password") )
                server.endSession(session)
                return -1
            #end
            #API to fetch all sale order information###################################################
            listcreditmemo = server.call(session, 'order_creditmemo.list',[{'updated_at': {'from':last_import}}])
            all_increment_id=[]
            all_customer_id=[]
            for credit in listcreditmemo:
                all_increment_id.append(credit['increment_id'])
            listorder = server.call(session, 'customapi_order_creditmemo.itemslist',[all_increment_id]) 
            credit_invoice=[]  
            for creditmemo in  listorder:
                    product = {}
                    return_to_stock = {}
                    product['magento_creditmemo_id']=int(creditmemo['creditmemo_id'])
                    if self.pool.get('stock.picking').search(cr,uid,[('magento_creditmemo_id','=',product['magento_creditmemo_id'])]):
                        continue
                    if self.pool.get('account.invoice').search(cr,uid,[('magento_creditmemo_id','=',product['magento_creditmemo_id'])]):
                        continue
                    magento_increment = creditmemo['order_id']
                    sale_order = self.pool.get('sale.order').search(cr,uid,[('magento_id','=',magento_increment)])
                    sale_obj = self.pool.get('sale.order').browse(cr,uid,sale_order)[0]
                    customer_id = sale_obj.partner_id.id
                    if creditmemo['items']:
                                for item in creditmemo['items']:
                                     product[item['product_id']]=float(item['qty'])
                                     return_to_stock[item['product_id']]=item.has_key('back_to_stock') and item['back_to_stock']
                                picking_ids = self.pool.get('stock.picking').search(cr,uid,[('type','=','out'),('sale_id','=',sale_order[0])])
                                for pick_id in picking_ids:
                                        context1={'active_id':pick_id,'active_ids':[pick_id]}
                                        mod_obj = self.pool.get('ir.model.data')
                                        act_obj = self.pool.get('ir.actions.act_window')
                                        result = mod_obj.get_object_reference(cr, uid, 'stock', 'act_stock_return_picking')
                                        id = result and result[1] or False
                                        result = act_obj.read(cr, uid, [id], context={})[0]
                                        context1['magento']=creditmemo['increment_id']+' for order '+ sale_obj.name
                                        context1['increment_id']=creditmemo['increment_id']
                                        try:
                                             return_picking_id = self.pool.get('stock.return.picking').create(cr,uid,result,context1)
                                        except Exception,e:
                                             continue
                                        result = self.pool.get('stock.return.picking').create_returns_from_magento(cr,uid,[return_picking_id],product,return_to_stock,creditmemo,context1)
                                        start = result['domain'][1:-1].index('[')
                                        stop = result['domain'][1:-1].index(']')
                                        inv_id = result['domain'][1:-1][start+1:stop]
                                        if creditmemo['base_adjustment_positive'] and float(creditmemo['base_adjustment_positive']):
                                                    product_id = self.pool.get('product.product').search(cr,uid,[('name','=','Refund Amount')])
                                                    if not product_id:
                                                          raise osv.except_osv(_('There is no refund product!'),_("There is no product with name 'Refund Amount', please create.") )
                                                    product_obj = self.pool.get('product.product').browse(cr,uid,product_id)[0]
                                                    a_m_l = {}
                                                    a_m_l['origin']=sale_obj.name
                                                    a_m_l['product_id']=product_id[0]
                                                    a_m_l['name']=product_obj.name
                                                    a_m_l['invoice_id']=inv_id
                                                    a_m_l['price_unit']=creditmemo['base_adjustment_positive']
                                                    a_m_l['partner_id']=customer_id
                                                    self.pool.get('account.invoice.line').create(cr,uid,a_m_l)
                                        
                                        if creditmemo['base_adjustment_negative'] and float(creditmemo['base_adjustment_negative']):
                                                    product_id = self.pool.get('product.product').search(cr,uid,[('default_code','ilike','Adjustment Fee')])
                                                    if not product_id:
                                                          raise osv.except_osv(_('There is no Adjustment Fee product!'),_("There is no product with Internal Reference 'Adjustment Fee', please create.") )
                                                    product_obj = self.pool.get('product.product').browse(cr,uid,product_id)[0]
                                                    a_m_l = {}
                                                    a_m_l['origin']=sale_obj.name
                                                    a_m_l['product_id']=product_id[0]
                                                    a_m_l['name']=product_obj.default_code and '['+product_obj.default_code+']'+product_obj.name or product_obj.name
                                                    a_m_l['invoice_id']=inv_id
                                                    a_m_l['price_unit']=-float(creditmemo['base_adjustment_negative'])
                                                    a_m_l['partner_id']=customer_id
                                                    self.pool.get('account.invoice.line').create(cr,uid,a_m_l)
                                        
                                        if creditmemo['base_shipping_amount'] and float(creditmemo['base_shipping_amount']):
                                                    product_id = magento_configuration_object[0].shipping_product.id
                                                    product_obj = magento_configuration_object[0].shipping_product.name
                                                    a_m_l = {}
                                                    a_m_l['origin']=sale_obj.name
                                                    a_m_l['product_id']=product_id
                                                    a_m_l['name']=product_obj
                                                    a_m_l['invoice_id']=inv_id
                                                    a_m_l['price_unit']=creditmemo['base_shipping_incl_tax']
                                                    a_m_l['partner_id']=customer_id
                                                    
                                                    if creditmemo['base_shipping_tax_amount'] and creditmemo['base_shipping_amount']:
                                                          try:
                                                             tax_percent = float(creditmemo['base_shipping_tax_amount'])/float(creditmemo['base_shipping_amount'])*100
                                                             tax_id = self.pool.get('magento.configuration').get_tax_id(cr, uid, tax_percent)
                                                             a_m_l['invoice_line_tax_id']=[[6,0,[tax_id]]]
                                                          except:
                                                                 pass
                                                    self.pool.get('account.invoice.line').create(cr,uid,a_m_l)     
                                               
                                        if result:
                                            credit_invoice.append(inv_id)
                                            total_no_of_records+=1
                    else:
                        refund={}
                        refund['date']=datetime.datetime.now()
                        journal_ids = self.pool.get('account.journal').search(cr,uid,[('type','=','sale_refund')])
                        refund['journal_id'] = journal_ids and journal_ids[0]
                        refund['filter_refund']='refund'
                        refund['description']="Magento Refund"
                        refund_id = self.pool.get('account.invoice.refund').create(cr,uid,refund)
                        context={}
                        if not sale_obj.invoice_ids:
                            continue
                        context['active_ids']=[sale_obj.invoice_ids[-1].id]
                        context['notax']=True
                        result = self.pool.get('account.invoice.refund').invoice_refund(cr,uid,[refund_id],context)
                        refund_inv_id=result['refunded_invoice_id'][0]
                        account_move_line_ids = self.pool.get('account.invoice.line').search(cr,uid,[('invoice_id','=',refund_inv_id)])
                        if account_move_line_ids:
                              self.pool.get('account.invoice.line').unlink(cr,uid,account_move_line_ids)
                              inv_tax_lines = self.pool.get('account.invoice.tax').search(cr,uid,[('invoice_id','=',refund_inv_id)])
                              self.pool.get('account.invoice.tax').unlink(cr,uid,inv_tax_lines)
                        product_id = self.pool.get('product.product').search(cr,uid,[('name','=','Refund Amount')])
                        if not product_id:
                              raise osv.except_osv(_('There is no refund product!'),_("There is no product with name 'Refund Amount', please create.") )
                        product_obj = self.pool.get('product.product').browse(cr,uid,product_id)[0]
                        a_m_l = {}
                        a_m_l['origin']=sale_obj.name
                        a_m_l['product_id']=product_id[0]
                        a_m_l['name']=product_obj.name
                        a_m_l['invoice_id']=refund_inv_id
                        a_m_l['price_unit']=creditmemo['base_adjustment_positive']
                        a_m_l['partner_id']=customer_id
                        self.pool.get('account.invoice.line').create(cr,uid,a_m_l)
                        if creditmemo['base_shipping_amount'] and float(creditmemo['base_shipping_amount']):
                                product_id = magento_configuration_object[0].shipping_product.id
                                product_obj = magento_configuration_object[0].shipping_product.name
                                a_m_l = {}
                                a_m_l['origin']=sale_obj.name
                                a_m_l['product_id']=product_id
                                a_m_l['name']=product_obj
                                a_m_l['invoice_id']=refund_inv_id
                                a_m_l['price_unit']=creditmemo['base_shipping_incl_tax']
                                a_m_l['partner_id']=customer_id
                                
                                if creditmemo['base_shipping_tax_amount'] and creditmemo['base_shipping_amount']:
                                      try:
                                         tax_percent = float(creditmemo['base_shipping_tax_amount'])/float(creditmemo['base_shipping_amount'])*100
                                         tax_id = self.pool.get('magento.configuration').get_tax_id(cr, uid, tax_percent)
                                         a_m_l['invoice_line_tax_id']=[[6,0,[tax_id]]]
                                      except:
                                             pass
                                self.pool.get('account.invoice.line').create(cr,uid,a_m_l)
                        self.pool.get('account.invoice').write(cr,uid,[refund_inv_id],{'name':creditmemo['increment_id'],'origin':creditmemo['increment_id']+' of order '+creditmemo['order_increment_id'],'magento_creditmemo_id':product['magento_creditmemo_id'],'amount_tax':0.0})        
#                        tax_lines = self.pool.get('account.invoice.tax').search(cr,uid,[('invoice_id','=',refund_inv_id)])
#                        self.pool.get('account.invoice.tax').unlink(cr,uid,tax_lines)
                        cr.execute("insert into sale_order_invoice_rel (invoice_id,order_id)values(%s,%s)",(refund_inv_id,sale_obj.id))
                    total_no_of_records+=1
                    continue
#            if credit_invoice:
#                self.pool.get('account.invoice').button_reset_taxes(cr,uid,credit_invoice)       
            if magento_configuration_object[0].id:
                self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'last_imported_credit_timestamp':start_timestamp})    
                server.endSession(session)
                return total_no_of_records    
            server.endSession(session)
            return -1           
    
magento_configuration()    

class account_invoice_refund(osv.osv_memory):
      _inherit = 'account.invoice.refund'

      def compute_refund(self, cr, uid, ids, mode='refund', context=None):
                inv_obj = self.pool.get('account.invoice')
                reconcile_obj = self.pool.get('account.move.reconcile')
                account_m_line_obj = self.pool.get('account.move.line')
                mod_obj = self.pool.get('ir.model.data')
                act_obj = self.pool.get('ir.actions.act_window')
                wf_service = netsvc.LocalService('workflow')
                inv_tax_obj = self.pool.get('account.invoice.tax')
                inv_line_obj = self.pool.get('account.invoice.line')
                res_users_obj = self.pool.get('res.users')
                if context is None:
                    context = {}
        
                for form in self.browse(cr, uid, ids, context=context):
                    created_inv = []
                    date = False
                    period = False
                    description = False
                    company = res_users_obj.browse(cr, uid, uid, context=context).company_id
                    journal_id = form.journal_id.id
                    for inv in inv_obj.browse(cr, uid, context.get('active_ids'), context=context):
                        if inv.state in ['draft', 'proforma2', 'cancel']:
                            raise osv.except_osv(_('Error!'), _('Cannot %s draft/proforma/cancel invoice.') % (mode))
                        if inv.reconciled and mode in ('cancel', 'modify'):
                            raise osv.except_osv(_('Error!'), _('Cannot %s invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.') % (mode))
                        if form.period.id:
                            period = form.period.id
                        else:
                            period = inv.period_id and inv.period_id.id or False
        
                        if not journal_id:
                            journal_id = inv.journal_id.id
        
                        if form.date:
                            date = form.date
                            if not form.period.id:
                                    cr.execute("select name from ir_model_fields \
                                                    where model = 'account.period' \
                                                    and name = 'company_id'")
                                    result_query = cr.fetchone()
                                    if result_query:
                                        cr.execute("""select p.id from account_fiscalyear y, account_period p where y.id=p.fiscalyear_id \
                                            and date(%s) between p.date_start AND p.date_stop and y.company_id = %s limit 1""", (date, company.id,))
                                    else:
                                        cr.execute("""SELECT id
                                                from account_period where date(%s)
                                                between date_start AND  date_stop  \
                                                limit 1 """, (date,))
                                    res = cr.fetchone()
                                    if res:
                                        period = res[0]
                        else:
                            date = inv.date_invoice
                        if form.description:
                            description = form.description
                        else:
                            description = inv.name
        
                        if not period:
                            raise osv.except_osv(_('Insufficient Data!'), \
                                                    _('No period found on the invoice.'))
        
                        refund_id = inv_obj.refund(cr, uid, [inv.id], date, period, description, journal_id, context=context)
                        refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
                        inv_obj.write(cr, uid, [refund.id], {'date_due': date,
                                                        'check_total': inv.check_total})
                        inv_obj.button_compute(cr, uid, refund_id)
        
                        created_inv.append(refund_id[0])
                        if mode in ('cancel', 'modify'):
                            movelines = inv.move_id.line_id
                            to_reconcile_ids = {}
                            for line in movelines:
                                if line.account_id.id == inv.account_id.id:
                                    to_reconcile_ids[line.account_id.id] = [line.id]
                                if type(line.reconcile_id) != osv.orm.browse_null:
                                    reconcile_obj.unlink(cr, uid, line.reconcile_id.id)
                            wf_service.trg_validate(uid, 'account.invoice', \
                                                refund.id, 'invoice_open', cr)
                            refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
                            for tmpline in  refund.move_id.line_id:
                                if tmpline.account_id.id == inv.account_id.id:
                                    to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                            for account in to_reconcile_ids:
                                account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                                                writeoff_period_id=period,
                                                writeoff_journal_id = inv.journal_id.id,
                                                writeoff_acc_id=inv.account_id.id
                                                )
                            if mode == 'modify':
                                invoice = inv_obj.read(cr, uid, [inv.id],
                                            ['name', 'type', 'number', 'reference',
                                            'comment', 'date_due', 'partner_id',
                                            'partner_insite', 'partner_contact',
                                            'partner_ref', 'payment_term', 'account_id',
                                            'currency_id', 'invoice_line', 'tax_line',
                                            'journal_id', 'period_id'], context=context)
                                invoice = invoice[0]
                                del invoice['id']
                                invoice_lines = inv_line_obj.read(cr, uid, invoice['invoice_line'], context=context)
                                invoice_lines = inv_obj._refund_cleanup_lines(cr, uid, invoice_lines)
                                tax_lines = inv_tax_obj.read(cr, uid, invoice['tax_line'], context=context)
                                tax_lines = inv_obj._refund_cleanup_lines(cr, uid, tax_lines)
                                invoice.update({
                                    'type': inv.type,
                                    'date_invoice': date,
                                    'state': 'draft',
                                    'number': False,
                                    'invoice_line': invoice_lines,
                                    'tax_line': tax_lines,
                                    'period_id': period,
                                    'name': description
                                })
                                for field in ('partner_id', 'account_id', 'currency_id',
                                                 'payment_term', 'journal_id'):
                                        invoice[field] = invoice[field] and invoice[field][0]
                                inv_id = inv_obj.create(cr, uid, invoice, {})
                                if inv.payment_term.id:
                                    data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv.payment_term.id, date)
                                    if 'value' in data and data['value']:
                                        inv_obj.write(cr, uid, [inv_id], data['value'])
                                created_inv.append(inv_id)
                    xml_id = (inv.type == 'out_refund') and 'action_invoice_tree1' or \
                             (inv.type == 'in_refund') and 'action_invoice_tree2' or \
                             (inv.type == 'out_invoice') and 'action_invoice_tree3' or \
                             (inv.type == 'in_invoice') and 'action_invoice_tree4'
                    result = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
                    id = result and result[1] or False
                    result = act_obj.read(cr, uid, id, context=context)
                    invoice_domain = eval(result['domain'])
                    invoice_domain.append(('id', 'in', created_inv))
                    result['domain'] = invoice_domain
                    result['refunded_invoice_id']=created_inv
                    return result



account_invoice_refund()

