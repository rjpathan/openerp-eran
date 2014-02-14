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


class credit_report(osv.osv_memory):
    
    
    _name="credit.report"
    
    
    _columns={
              'period_ids': fields.many2one('account.period', 'Zeiträume'),
              'date_id':fields.date('Startdatum'),
              'date_end':fields.date('Enddatum'),
              'status': fields.selection([ ('all', 'All'),('open', 'open'),('closed','closed')],'Gutschrift(Credit Note) Status'),
           
              }
    
    def report_credit(self,cr,uid,ids,context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'Credit_report',
            'datas': datas,
            } 
    
    
    
credit_report()
