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





class magento_report(osv.osv_memory):
    
    
    _name="magento.report"
    
    _columns={
              'date_id':fields.date('Date'),
            
              }
    
    def report_magento(self,cr,uid,ids,context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'magento_daily_report',
            'datas': datas,
            } 
    
    
    
magento_report()



class magento_report_month(osv.osv_memory):
    
    
    _name="magento.report.month"
    
    def _get_month(self,cr,uid,context=None):
        lst=[]
        mon=['','January','February','March','April','May','June','July','August','September','October','Novenber','December']
        for i in range(1,13):
            lst.append((i,mon[i]))
        return lst
    
    def _get_year(self,cr,uid,context=None):
        lst=[]
        year_ids=self.pool.get('account.fiscalyear').search(cr,uid,[])
        year_objs=self.pool.get('account.fiscalyear').browse(cr,uid,year_ids)
        for obj in year_objs:
            lst.append((obj.name,obj.name))
        return lst
    
    
    _columns={
            #  'date_id':fields.date('Date'),
               'month_id':fields.selection(_get_month,"month"),
                'year_id':fields.selection(_get_year,"year")
             
             
              }
    
   
    
    
    
    
    
    def magento_month(self,cr,uid,ids,context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'magento_monthly_report',
            'datas': datas,
            } 
    
    
    
magento_report_month()    



    