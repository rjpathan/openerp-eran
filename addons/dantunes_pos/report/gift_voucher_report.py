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
import time
from report import report_sxw
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools import to_xml

from openerp.tools.translate import _


class gift_voucher_parse(report_sxw.rml_parse):


    def __init__(self, cr, uid, name, context=None):
        self.total = 0.0
        self.open_amount = 0.0
        self.closed_amount = 0.0
        self.count = 0
        self.totalcount = 0
        self.open = 0
        super(gift_voucher_parse,self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_details':self.get_details,
            'get_total':self.get_total,
            'get_count':self.get_count,
            'get_totalcount':self.get_totalcount,
            'get_open':self.get_open,
            'get_header':self.get_header,
            'get_openamount':self.get_openamount,
            'get_closedamount':self.get_closedamount,

       })
    def get_total(self,data):        
        return self.total
    def get_count(self,data):        
        return self.count
    def get_totalcount(self,data):        
        return self.totalcount
    def get_open(self,data):        
        return self.open
    def get_openamount(self,data):        
        return self.open_amount
    def get_closedamount(self,data):        
        return self.closed_amount
    def get_header(self,data):
        header='Gutschein Bericht'
        month=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
        date=data['form']['date_id']
        date_end=data['form']['date_end']
        period=data['form']['period_ids']
        if period:
            print period,'period----------'
            period_obj=self.pool.get('account.period').browse(self.cr,self.uid,period[0])
            mon_name=month[datetime.strptime(period_obj.date_start,'%Y-%m-%d').month]
            header+=(' vom '+mon_name)
        if date and date_end:
            date_st=datetime.strptime(date,'%Y-%m-%d').strftime('%d.%m.%Y')
            date_stop=datetime.strptime(date_end,'%Y-%m-%d').strftime('%d.%m.%Y')
            header+=(' von '+date_st+' bis '+date_stop)
        elif date:
            date_on=datetime.strptime(date,'%Y-%m-%d').strftime('%d.%m.%Y')
            header+=(' vom '+date_on)
        return header
    def get_details(self,data):
        
        date=data['form']['date_id']
        date_end=data['form']['date_end']
        period=data['form']['period_ids']
        status=data['form']['status']
        total = 0
        count = 0
        result=[]
        if date and date_end:
            start=datetime.strptime(date,'%Y-%m-%d')
            stop=datetime.strptime(date_end,'%Y-%m-%d')
            diff=stop-start
            if diff.days<0:
                raise osv.except_osv(_('Warning!'),_('Das Enddatum muss nach dem Startdatum liegen oder das gleiche Datum haben.'))
        args=[('gift_card','=','true'),('return','=',False)]
        date1=' 00:00:01'
        date2=' 23:59:59'
        if date:
            date1=date+date1
            if date_end:
                date2=date_end+date2
            else:
                date2=date+date2
            args.append(('date_order','>=',date1))
            args.append(('date_order','<=',date2))
        if period:
            period_obj=self.pool.get('account.period').browse(self.cr,self.uid,period[0])
            date1=period_obj.date_start+date1
            date2=period_obj.date_stop+date2
            args.append(('date_order','>=',date1))
            args.append(('date_order','<=',date2))
        if status:
            if status=='open':
                args.append(('closed','=',False))
            if status=='closed':
                args.append(('closed','=',True))
                
        order_ids=self.pool.get('pos.order').search(self.cr,self.uid,args)
        for order_id in order_ids:
            order_obj=self.pool.get('pos.order').browse(self.cr,self.uid,order_id)
            res = order_obj.amount_total
            if order_obj.closed:
                order_obj.closed = 'Closed'
                if status in ['open','closed']:
                    self.totalcount += 1
                else:
                    self.count += 1
                    self.closed_amount += res
            else:
                order_obj.closed = 'Open'
                if status in ['open','closed']:
                    self.totalcount += 1
                else:
                    self.open += 1
                    self.open_amount += res
            dic = {
                        'date' : datetime.strptime(order_obj.date_order,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d'),
                        'closeddate':order_obj.redeem_date,
                        'reference' : order_obj.pos_reference,
                        'status' : order_obj.closed,
                        'amount' : res,
            }
            result.append(dic)
            self.total += res
        return result

report_sxw.report_sxw('report.gift_voucher_report', 'pos.order', 'addons/dantunes_pos/report/gift_voucher_report.rml', parser=gift_voucher_parse, header=False)