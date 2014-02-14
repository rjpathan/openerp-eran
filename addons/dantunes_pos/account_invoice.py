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

from datetime import datetime, date
from lxml import etree
import time
import unicodedata
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
import re
import datetime
import HTMLParser
import base64
import HTMLParser

class account_invoice_line(osv.osv):
    _inherit="account.invoice.line"
    
    def _display(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for invoice_line in self.browse(cr, uid, ids, context=context):
            result[invoice_line.id] = False
            if invoice_line.invoice_id.magento_creditmemo_id and invoice_line.invoice_id.type=="out_refund" and invoice_line.invoice_id.state=="paid" and invoice_line.product_id.type!='service':
                result[invoice_line.id] = True
        return result
    
    _columns={
              'stock_update':fields.boolean('Stock Update'),
              'move_id':fields.many2one('stock.move',"Move Line"),
              'display':fields.function(_display,type="boolean",string="Display"),
              'scrapped':fields.boolean('Scrapped'),
              }
    
    def create_scrap_move(self,cr,uid,ids,context):
        for line in self.browse(cr,uid,ids):
            if line.stock_update:
                self.write(cr,uid,ids,{'scrapped':True,'stock_update':False})
            else:
                self.write(cr,uid,ids,{'scrapped':True})
            if not line.scrapped and line.invoice_id.state=="paid":
                origin=""
                move_obj=self.pool.get('stock.move')
                scrap_loc=self.pool.get('stock.location').search(cr,uid,[('scrap_location','=',True)])
                inv_origin=line.origin.split(':')
                if len(inv_origin)>=2:
                    origin=inv_origin[0]+'-'+line.invoice_id.name+':'+inv_origin[1]
                else:
                    origin=line.invoice_id.name+':'+inv_origin[0]
		try:
                    vals={
                           'location_id':line.move_id.location_dest_id.id,
                           'location_dest_id':scrap_loc[0],
                           'origin':origin,
                           'type':'internal'
                          }
                    res_id=move_obj.copy(cr,uid,line.move_id.id,vals)
                    move_obj.action_done(cr, uid, [res_id], context=context)
                except Exception,e:
                    raise osv.except_osv(_('Warning!'),_('Dieser Artikel ist bereits beschädigt.'))
        return True
    
account_invoice_line()

class account_bank_statement(osv.osv):
    _inherit="account.bank.statement"
    
    def _prepare_move(self, cr, uid, st_line, st_line_number, context=None):
        result=super(account_bank_statement,self)._prepare_move(cr, uid, st_line, st_line_number, context)
        order=st_line.name.split(':')[0]
        pos_order=self.pool.get('pos.order').search(cr,uid,[('name','=',order)])
        if pos_order:
            pos_order_obj=self.pool.get('pos.order').browse(cr,uid,pos_order[0])
            if pos_order_obj.amount_total<0.0:
                result['closed']=False
		ref_num=pos_order_obj.pos_reference.split('Order ')
		if len(ref_num)>=2:
			result['pos_reference']=ref_num[1]
		else:
                	result['pos_reference']=pos_order_obj.pos_reference
                if st_line.journal_id.code.lower()=='cmemo' and st_line.amount<0.0:
                    result['credit_note']=True
        return result
    
account_bank_statement()

class account_move(osv.osv):
    _inherit="account.move"
    
    _columns={
              'closed':fields.boolean("Closed"),
              'pos_reference':fields.char('Order reference',size=128),
              'credit_note':fields.boolean('credit note'),
              'closed_date': fields.date('Redeemed Date'),
              }
    _defaults={
               "closed":True,
		"credit_note":False,
               }
account_move()

class account_journal(osv.osv):
    _inherit="account.journal"
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if context==None:
            context={}
        if context.has_key('pos_return_pay') and context['pos_return_pay']=='return' and context.has_key('order_id'):
            if args==None:
                args=[]
            order_obj=self.pool.get('pos.order').browse(cr,user,context['order_id'])
            ids=[x.id for x in order_obj.session_id.config_id.journal_ids]
            args.append(('id','in',ids))
        return super(account_journal,self).name_search(cr,user,name,args,operator,context,limit)
    
account_journal()

class pos_make_payment(osv.osv_memory):
    _inherit="pos.make.payment"
    
    def _get_order(self,cr,uid,context):
        if context.has_key('active_model') and context['active_model']=='pos.order':
            active_id = context and context.get('active_id', False)
            if active_id:
                return active_id
        return False
    
    _columns={
              'order_id':fields.many2one('pos.order','POS Order'),
              }
    
    _defaults={
               'order_id':_get_order
               }
    
pos_make_payment()

class account_invoice(osv.osv):
    _inherit="account.invoice"
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        type_inv = context.get('type', 'out_invoice')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        type2journal = {'out_invoice': 'sale', 'in_invoice': 'purchase', 'out_refund': 'sale_refund', 'in_refund': 'purchase_refund'}
        journal_obj = self.pool.get('account.journal')
        args=[('type', '=', type2journal.get(type_inv, 'sale')),('company_id', '=', company_id)]
        if type2journal.get(type_inv, 'sale')=='sale':
            args.append(('code','not ilike','gcard'))
        res = journal_obj.search(cr, uid, args,limit=1)
        return res and res[0] or False
    
    def create(self,cr,uid,vals,context=None):
        journal_ids=self.pool.get('account.journal').search(cr,uid,[('code','ilike','GCard')])
        if vals.has_key('company_id'):
            sale_journals=self.pool.get('account.journal').search(cr,uid,[('type','=','sale'),('company_id','=',vals['company_id'])])
        else:
            sale_journals=self.pool.get('account.journal').search(cr,uid,[('type','=','sale')])
        if vals.has_key('journal_id') and (vals['journal_id'] in journal_ids):
            sale_journal_ids=list(set(sale_journals)-set(journal_ids))
            vals['journal_id']=sale_journal_ids[0]
        return super(account_invoice,self).create(cr,uid,vals,context)    
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}

        if context.get('active_model', '') in ['res.partner'] and context.get('active_ids', False) and context['active_ids']:
            partner = self.pool.get(context['active_model']).read(cr, uid, context['active_ids'], ['supplier','customer'])[0]
            if not view_type:
                view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.invoice.tree')])
                view_type = 'tree'
            if view_type == 'form':
                if partner['supplier'] and not partner['customer']:
                    view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'account.invoice.supplier.form')])
                elif partner['customer'] and not partner['supplier']:
                    view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'account.invoice.form')])
        if view_id and isinstance(view_id, (list, tuple)):
            view_id = view_id[0]
        res = super(account_invoice,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        type = context.get('journal_type', False)
        for field in res['fields']:
            if field == 'journal_id' and type:
                args=[('type', '=', type)]
                if type=='sale':
                    args.append(('code','not ilike','gcard'))
                journal_select = journal_obj._name_search(cr, uid, '', args, context=context, limit=None, name_get_uid=1)
                res['fields'][field]['selection'] = journal_select

        doc = etree.XML(res['arch'])

        if context.get('type', False):
            for node in doc.xpath("//field[@name='partner_bank_id']"):
                if context['type'] == 'in_refund':
                    node.set('domain', "[('partner_id.ref_companies', 'in', [company_id])]")
                elif context['type'] == 'out_refund':
                    node.set('domain', "[('partner_id', '=', partner_id)]")
            res['arch'] = etree.tostring(doc)

        if view_type == 'search':
            if context.get('type', 'in_invoice') in ('out_invoice', 'out_refund'):
                for node in doc.xpath("//group[@name='extended filter']"):
                    doc.remove(node)
            res['arch'] = etree.tostring(doc)

        if view_type == 'tree':
            partner_string = _('Customer')
            if context.get('type', 'out_invoice') in ('in_invoice', 'in_refund'):
                partner_string = _('Supplier')
                for node in doc.xpath("//field[@name='reference']"):
                    node.set('invisible', '0')
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set('string', partner_string)
            res['arch'] = etree.tostring(doc)
        return res
    
account_invoice()
