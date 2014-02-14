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

class daily_pos_wizard(osv.osv_memory):
    _name='daily.pos.wizard'
    
    def _get_shops(self,cr,uid,context=None):
        lst=[]
        shop_ids=self.pool.get('sale.shop').search(cr,uid,[])
        shop_objs=self.pool.get('sale.shop').browse(cr,uid,shop_ids)
        for obj in shop_objs:
            lst.append((obj.name,obj.name))
        return lst
    
    def daily_report(self,cr,uid,ids,context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        datas = {
             'ids': [],
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos_daily_report',
            'datas': datas,
            }  
          
    
    _columns={
              'pos_shop':fields.selection(_get_shops,'Shop'),
              'date':fields.date('Date')
              }

daily_pos_wizard()

class monthly_pos_wizard(osv.osv_memory):
    _name='monthly.pos.wizard'
    
    def monthly_report(self,cr,uid,ids,context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        datas = {
             'ids': [],
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos_monthly_report',
            'datas': datas,
            } 
        
    def _get_shops(self,cr,uid,context=None):
        lst=[]
        shop_ids=self.pool.get('sale.shop').search(cr,uid,[])
        shop_objs=self.pool.get('sale.shop').browse(cr,uid,shop_ids)
        for obj in shop_objs:
            lst.append((obj.name,obj.name))
        return lst
    
    def _get_year(self,cr,uid,context=None):
        lst=[]
        year_ids=self.pool.get('account.fiscalyear').search(cr,uid,[])
        year_objs=self.pool.get('account.fiscalyear').browse(cr,uid,year_ids)
        for obj in year_objs:
            lst.append((obj.name,obj.name))
        return lst
    
    def _get_month(self,cr,uid,context=None):
        lst=[]
        mon=['','January','February','March','April','May','June','July','August','September','October','Novenber','December']
        for i in range(1,13):
            lst.append((i,mon[i]))
        return lst
    
    _columns={
              'pos_shop':fields.selection(_get_shops,'Shop'),
              'month':fields.selection(_get_month,'Month'),
              'year':fields.selection(_get_year,'Year')
              }
monthly_pos_wizard()