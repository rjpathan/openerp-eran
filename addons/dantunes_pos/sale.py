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

class account_invoice(osv.osv):
    _inherit="account.invoice"
    _order="date_invoice desc"


class stock_picking_out(osv.osv):
    _inherit="stock.picking.out"
    _order="date desc"


class stock_picking_in(osv.osv):
    _inherit="stock.picking.in"
    _order="date desc"
    
class stock_picking(osv.osv):
    _inherit="stock.picking"
    _order="date desc"
    
class sale_order(osv.osv):
    _inherit="sale.order"
    _order="id desc"
    
    html=HTMLParser.HTMLParser()
    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        res_id=''
        if 'Invoice and DHL Shipment PDF' in msg.get('subject'):
            body=msg.get('body')
            data = msg.get('body')
            data=self.html.unescape(data)
            data = data.replace("\n", " ")
            data = data.replace("\r", " ")
            data = " ".join(data.split())  
            p = re.compile(r'')
            data = p.sub('', data)
            p = re.compile(r'<[^<]*?>')
            data = p.sub('', data)
            num=data.split('order#')[-1].strip()
            sale_ids=self.pool.get('sale.order').search(cr,uid,[('magento_id','=',num)])
            if sale_ids:
                res_id=sale_ids[0]
                self.pool.get('sale.order').write(cr,uid,sale_ids,{'has_attachment':True})
        return res_id
    
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                        subtype=None, parent_id=False, attachments=None, context=None, **kwargs):
        """ Post a new message in an existing thread, returning the new
            mail.message ID. Extra keyword arguments will be used as default
            column values for the new mail.message record.
            Auto link messages for same id and object
            :param int thread_id: thread ID to post into, or list with one ID;
                if False/0, mail.message model will also be set as False
            :param str body: body of the message, usually raw HTML that will
                be sanitized
            :param str subject: optional subject
            :param str type: mail_message.type
            :param int parent_id: optional ID of parent message in this thread
            :param tuple(str,str) attachments or list id: list of attachment tuples in the form
                ``(name,content)``, where content is NOT base64 encoded
            :return: ID of newly created mail.message
        """
        if context is None:
            context = {}
        if attachments is None:
            attachments = {}

        assert (not thread_id) or isinstance(thread_id, (int, long)) or \
            (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), "Invalid thread_id; should be 0, False, an ID or a list with one ID"
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id and thread_id[0]
        mail_message = self.pool.get('mail.message')
        model = context.get('thread_model', self._name) if thread_id else False

        attachment_ids = kwargs.pop('attachment_ids', [])
        for name, content in attachments:
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            data_attach = {
                'name': name,
                'datas': base64.b64encode(str(content)),
                'datas_fname': name,
                'description': name,
                'res_model': context.get('thread_model') or self._name,
                'res_id': thread_id,
            }
            attachment_ids.append((0, 0, data_attach))

        # fetch subtype
        if subtype:
            s_data = subtype.split('.')
            if len(s_data) == 1:
                s_data = ('mail', s_data[0])
            ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, s_data[0], s_data[1])
            subtype_id = ref and ref[1] or False
        else:
            subtype_id = False

        # _mail_flat_thread: automatically set free messages to the first posted message
        if self._mail_flat_thread and not parent_id and thread_id:
            message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id), ('model', '=', model)], context=context, order="id ASC", limit=1)
            parent_id = message_ids and message_ids[0] or False
        # we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
        elif parent_id:
            message_ids = mail_message.search(cr, SUPERUSER_ID, [('id', '=', parent_id), ('parent_id', '!=', False)], context=context)
            # avoid loops when finding ancestors
            processed_list = []
            if message_ids:
                message = mail_message.browse(cr, SUPERUSER_ID, message_ids[0], context=context)
                while (message.parent_id and message.parent_id.id not in processed_list):
                    processed_list.append(message.parent_id.id)
                    message = message.parent_id
                parent_id = message.id
        if self._name=='sale.order':
            type='notification'
        user_obj=self.pool.get('res.users').browse(cr,uid,uid)
        values = kwargs
        values.update({
            'model': model or self._name,
            'res_id': thread_id or False,
            'body': body,
            'subject': subject or False,
            'type': type,
            'parent_id': parent_id,
            'attachment_ids': attachment_ids,
            'subtype_id': subtype_id,
        })
        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)
            
        mail_message = mail_message.create(cr, uid, values, context=context)
        mail_not = self.pool.get('mail.notification').search(cr,uid,[('message_id','=',mail_message)])
        print "mail_not...",mail_not
        print self.pool.get('mail.notification').write(cr,uid,mail_not,{'read':True})
        return mail_message
    
sale_order()

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    def _get_location(self,cr,uid,ids,name,args,context=None):
        """To get current location of the product"""
        res={}
        for line in  self.browse(cr,uid,ids):
                     id = line.procurement_id and line.procurement_id.location_id.id
                     if not id:
                        id = line.order_id.shop_id.warehouse_id.lot_stock_id.id
                     res[line.id]= id or False
        return res             
                    
    _columns = {
                   'location_id':fields.function(_get_location,relation="stock.location" ,type="many2one", string="Location")
                }
sale_order_line()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
                'stock_update':fields.boolean(""),
                'magento_increment_id':fields.char("Magento increment number"),
                }
    
    def get_other_location(self,cr,uid,location_dest,context):
        location = self.pool.get('stock.location').search(cr,uid,[('scrap_location','=',True)])
        value = {}
        value['location_dest_id'] = location[0]
        return {'value':value}
    
stock_move()    