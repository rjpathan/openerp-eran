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


class credit_memo_kt(report_sxw.rml_parse):


    def __init__(self, cr, uid, name, context=None):
        self.total = 0.0
        self.open_amount = 0.0
        self.closed_amount = 0.0
        self.count = 0
        self.totalcount = 0
        self.open = 0
        super(credit_memo_kt, self).__init__(cr, uid, name, context=context)
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
        header='Gutschrift Bericht'
        month=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
        date=data['form']['date_id']
        date_end=data['form']['date_end']
        period=data['form']['period_ids']
        if period:
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
        if not date and not period and not status:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('credit_note','=','true')])
            for journal_id in journal_ids:
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    self.count += 1
                    self.closed_amount += res
                else:
                    journal_obj.closed = 'Open'
                    self.open += 1
                    self.open_amount += res
                dic = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                
                result.append(dic)
                self.total += res
        elif date and not period and not status:
            if date_end:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','>=',date),('date','<=',date_end),('credit_note','=','true')])
            else:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','=',date),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    self.count += 1
                    self.closed_amount += res
                else:
                    journal_obj.closed = 'Open'
                    self.open += 1
                    self.open_amount += res
                dic = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                
                result.append(dic)
                self.total += res
        elif date and status == 'all' and not period:
            if date_end:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','>=',date),('date','<=',date_end),('credit_note','=','true')])
            else:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','=',date),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    self.count += 1
                    self.closed_amount += res
                else:
                    journal_obj.closed = 'Open'
                    self.open += 1
                    self.open_amount += res
                dic = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic)
                self.total += res
               
        elif date and status == 'open' and not period:
            if date_end:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','>=',date),('date','<=',date_end),('closed','!=','true'),('credit_note','=','true')])
            else:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','=',date),('closed','!=','true'),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    
                else:
                    journal_obj.closed = 'Open'
                dic = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic)
                self.total += res
                self.totalcount += 1
                
        elif date and status == 'closed' and not period:
            if date_end:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','>=',date),('date','<=',date_end),('closed','=','true'),('credit_note','=','true')])
            else:
                journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('date','=',date),('closed','=','true'),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                else:
                    journal_obj.closed = 'Open'
                dic = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic)
                self.total += res
                self.totalcount += 1
            
        elif period and not date and not status:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('period_id','=',period[0]),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    self.count += 1
                    self.closed_amount += res
                else:
                    journal_obj.closed = 'Open'
                    self.open += 1
                    self.open_amount += res
                dic1 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic1)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
                
        elif period and status == 'all' and not date:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('period_id','=',period[0]),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    self.count += 1
                    self.closed_amount += res
                else:
                    journal_obj.closed = 'Open'
                    self.open += 1
                    self.open_amount += res
                dic2 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic2)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
                
        elif period and status == 'open' and not date:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('period_id','=',period[0]),('closed','!=','true'),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                else:
                    journal_obj.closed = 'Open'
                dic2 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic2)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
                self.totalcount += 1
        elif period and status == 'closed' and not date:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('period_id','=',period[0]),('closed','=','true'),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                else:
                    journal_obj.closed = 'Open'
                dic2 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic2)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
                self.totalcount += 1
            
        elif status == 'all' and not date and not period:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                    self.count += 1
                    self.closed_amount += res
                else:
                    journal_obj.closed = 'Open'
                    self.open += 1
                    self.open_amount += res
                dic3 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic3)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
               
        elif status == 'open' and not date and not period:
           
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('closed','!=','true'),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                else:
                    journal_obj.closed = 'Open'
                dic4 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic4)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
                self.totalcount += 1
        elif status == 'closed' and not date and not period:
            journal_ids=self.pool.get('account.move').search(self.cr,self.uid,[('closed','=','true'),('credit_note','=','true')])
            for journal_id in journal_ids:
                
                journal_obj=self.pool.get('account.move').browse(self.cr,self.uid,journal_id)
                self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE move_id='%s'" 
                            %(journal_id))
                res = self.cr.fetchone()[0]
                if journal_obj.closed:
                    journal_obj.closed = 'Closed'
                else:
                    journal_obj.closed = 'Open'
                dic5 = {
                            'date' : journal_obj.date,
                            'closeddate':journal_obj.closed_date,
                            'reference' : journal_obj.pos_reference,
                            'status' : journal_obj.closed,
                            'amount' : res,
                            
                }
                result.append(dic5)
                result = sorted(result,key=lambda k: k['date'])
                self.total += res
                self.totalcount += 1
 
        return result
    
    
        

report_sxw.report_sxw('report.Credit_report', 'account.move', 'addons/dantunes_pos/report/credit_memo_report.rml', parser=credit_memo_kt, header=False)