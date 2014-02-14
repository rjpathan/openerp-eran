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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class stock_warehouse(osv.osv):
    _inherit="stock.warehouse"
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None,context=None, count=False):
        args.append('!')
        args.append(('name','ilike','your company'))
        return super(stock_warehouse,self).search(cr,uid,args,context=context)
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args.append('!')
        args.append(('name','ilike','your company'))
        return super(stock_warehouse,self).name_search(cr,user,name,args,operator,context,limit)
stock_warehouse()

class sale_shop(osv.osv):
    _inherit="sale.shop"
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None,context=None, count=False):
        args.append('!')
        args.append(('name','ilike','your company'))
        return super(sale_shop,self).search(cr,uid,args,context=context)
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args.append('!')
        args.append(('name','ilike','your company'))
        print cr,user,name,args,operator,context,limit,'----------'
        return super(sale_shop,self).name_search(cr,user,name,args,operator,context,limit)
stock_warehouse()