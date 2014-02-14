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

from osv import osv, fields
import math
import re
from tools.translate import _
import StringIO
import cStringIO
import base64
import xlrd
import string
import sys
import datetime

class product_product(osv.osv):
    _inherit ='product.product'
    ''' Adding  new fields not exist in openerp related to Sugarcrm'''
    
#    _columns ={
#               
#               'note':fields.text('Note'),
#               'tariff_code':fields.char('Tariff Code',size=16),
##               'status' : fields.selection([('active','Active'),('expired','Expired')], 'Tariff Status'),
#               'last_use_entry':fields.date('Last Use Entry')
#               
#               }
    
product_product()


class product_import(osv.osv):
    _name ="product.import"
    '''For improt products from files '''
    _columns ={
              'datas': fields.binary('Data'),
              'datas_fname': fields.char('Filename',size=256),
              'test':fields.boolean('Test') ,
               }
    def import_flash_data(self, cr, uid, ids, context=None):
        file_name2=self.browse(cr,uid,ids)[0].datas
        if not file_name2:
            raise osv.except_osv(_('File Not Chosen!'), _('Please Choose The File!'))
        #file_name1=self.browse(cr,uid,ids)[0].datas_fname  # file_name1 contain the path of the file and file_name2 contain the binary data of the file
        val=base64.decodestring(file_name2)
        fp = StringIO.StringIO()
        fp.write(val)     
        wb = xlrd.open_workbook(file_contents=fp.getvalue())
        wb.sheet_names()
        sheet_name=wb.sheet_names()
        # sh = wb.sheet_by_index(0)
        sh = wb.sheet_by_name(sheet_name[0])
        n_rows=sh.nrows
        product_obj=self.pool.get('product.product')
        #uom_obj=self.pool.get('product.uom')
       
        for r in range(1,n_rows):
            row=sh.row_values(r)
            prod_ids=self.pool.get('product.product').search(cr,uid,[('default_code','=',row[0])])
            if prod_ids:
                product_obj.write(cr,uid,prod_ids,{'magento_id':row[2]})
        return True 
product_import()





