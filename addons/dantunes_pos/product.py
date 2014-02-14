# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import datetime
from lxml import etree
import math
import pytz
import re

import openerp
from openerp import SUPERUSER_ID
from openerp import pooler, tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

class product_product(osv.osv):
    _inherit = 'product.product'
    
    def _product_qty_location(self,cr,uid,ids,field_names=None,args=None,context=None):
        if context==None:
            context={}
        res={}
        for id in ids:
            res[id]={}
            for field in field_names:
                context['location']=field.split('_')[-1]
                if context['location']=='webshop':
                    context['location']='web shop'
                res[id][field]=self._product_available(cr, uid,[id],['qty_available'], args, context)[id]['qty_available']
            del context['location']
        return res
    
    def _get_shop(self,cr,uid,ids,field_name,args,context=None):
        res={}
        for id in ids:
            if uid==1:
                res[id]='admin'
            else: 
                res[id]=self.pool.get('res.users').browse(cr,uid,uid).pos_config.shop_id.name
        return res
    
    _columns = {
                'magento_attr_id':fields.integer("Magento Attribute ID",help="Enter ID of Magento attribute set"),
                'sale_journal':fields.many2one('account.journal','Sales Journal'),
                'qty_available_freiburg': fields.function(_product_qty_location, type='float', string='Inventory Freiburg',multi='qty_by_loc'),
                'qty_available_konstanz': fields.function(_product_qty_location, type='float', string='Inventory Konstanz',multi='qty_by_loc'),
                'qty_available_webshop': fields.function(_product_qty_location, type='float', string='Inventory Webshop',multi='qty_by_loc'),
                'qty_available_stock': fields.function(_product_qty_location, type='float', string='Inventory Stock',multi='qty_by_loc'),
                'user_shop':fields.function(_get_shop,string='User Shop',type="char"),
                }   
    def export_magento_enable(self,cr,uid,ids,context=None):
            if 'active_ids' in context.keys():
                product_ids = context['active_ids']
                self.write(cr,uid,product_ids,{'export_to_magento':True})
            
    def export_magento_disable(self,cr,uid,ids,context=None):
            if 'active_ids' in context.keys():
                product_ids = context['active_ids']
                self.write(cr,uid,product_ids,{'export_to_magento':False})
product_product()          

class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
                'magento_attr_id':fields.integer("Magento Attribute ID",help="Enter ID of Magento attribute set")
                }      
product_template()   