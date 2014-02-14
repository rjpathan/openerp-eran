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
import re

class pos_daily_report_kt(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(pos_daily_report_kt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_address':self.get_address
            
       })
        
    def get_address(self,data):
        shop_id=self.pool.get('sale.shop').search(self.cr,self.uid,[('name','=',data['form']['pos_shop'])])
        shop_obj=self.pool.get('sale.shop').browse(self.cr,self.uid,shop_id)
#        add=shop_obj[0].address_id
        lst=[]
        date=data['form']['date']
        day_str=datetime.strptime(date,'%Y-%m-%d').strftime("%Y-%m-%d %H:%M:%S")
        day_end=datetime.strptime(date+' 23:56:56','%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M:%S")
        shop=data['form']['pos_shop']
        pos_conf_ids=self.pool.get('pos.config').search(self.cr,self.uid,[('shop_id.name','=',shop)])
        sess_ids=self.pool.get('pos.session').search(self.cr,self.uid,[('config_id','in',pos_conf_ids),('stop_at','>',day_str),('stop_at','<',day_end)])
        sess_objs=self.pool.get('pos.session').browse(self.cr,self.uid,sess_ids)
        for sess_obj in sess_objs:
            res={}
#            res['name']=add
            res['s_no']=sess_obj.id
            res['s_start']=sess_obj.start_at or ''
            res['s_stop']=sess_obj.stop_at or ''
            res['s_name']=sess_obj.name or ''
            res['s_user']=sess_obj.user_id.name or ''
            res['amt']=[]
            res['reason']=[]
            card_tax=0.0
            cash_tax=0.0
            if sess_obj:
                val={}
                val['name']='Morgens Anfangsbestand'
                val['no']=''
                val['net']=sess_obj.cash_register_balance_start-cash_tax or ''
                val['tax']=cash_tax
                val['gross']=sess_obj.cash_register_balance_start or ''
                res['amt'].append(val)
                val={}
                val['name']='kartenzahlungen'
                for i in sess_obj.statement_ids:
                    if i.journal_id.type=='bank':
                        card_obj=i
                        for line in i.line_ids:
                            if line.pos_statement_id.amount_tax:
                                card_tax+=line.pos_statement_id.amount_tax
                    elif i.journal_id.type=='cash':
                        cash_obj=i
                        for line in i.line_ids:
                            if line.pos_statement_id.amount_tax:
                                cash_tax+=line.pos_statement_id.amount_tax
                val['no']=len(card_obj.line_ids)
                val['net']=card_obj.balance_end_real-card_tax
                val['tax']=card_tax
                val['gross']=card_obj.balance_end_real
                res['amt'].append(val)
                val={}
                val['name']='BAR Buchungen'
                val['no']=len(cash_obj.line_ids)
                val['net']=cash_obj.balance_end_real-cash_tax
                val['tax']=cash_tax
                val['gross']=cash_obj.balance_end_real
                res['amt'].append(val)
                val={}
                val['name']='Einlagen'
                c,d,deposit,withdraw=0,0,0.0,0.0
                for ob in cash_obj.line_ids:
                    if ob.type=='general' and ob.amount>0:
                        c+=1
                        deposit+=ob.amount
                    elif ob.type=='general' and ob.amount<0:
                        d+=1
                        withdraw+=ob.amount
                        reason={}
                        reason['amount']=ob.amount
                        reason['reason']=ob.name
                        reason['time']=ob.date
                        res['reason'].append(reason)
                for ob in card_obj.line_ids:
                    if ob.type=='general' and ob.amount>0:
                        c+=1
                        deposit+=ob.amount
                    elif ob.type=='general' and ob.amount<0:
                        d+=1
                        withdraw+=ob.amount
                val['no']=c
                val['net']=deposit
                val['tax']=0.0
                val['gross']=val['net']+val['tax']
                res['amt'].append(val)
                val={}
                val['name']='Entnahmen'
                val['no']=d
                val['net']=withdraw
                val['tax']=0.0
                val['gross']=val['net']+val['tax']
                res['amt'].append(val)
                res['should_in_pos']=sess_obj.cash_register_balance_end
                res['actual_in_pos']=sess_obj.cash_register_balance_end_real
                lst.append(res)
        return lst
report_sxw.report_sxw('report.pos_daily_report', 'daily.pos.wizard', 'addons/dantunes_pos/report/pos_daily_report.rml', parser=pos_daily_report_kt, header=False)

class pos_monthly_report_kt(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(pos_monthly_report_kt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_address':self.get_address,
            'get_session_details':self.get_session_details,
            'get_totals':self.get_totals
       })
    cash_total=0.0
    card_total=0.0
    deposit_total=0.0
    withdraw_total=0.0
        
    def get_address(self,data):
        print data,'data------------------'
        shop_id=self.pool.get('sale.shop').search(self.cr,self.uid,[('name','=',data['form']['pos_shop'])])
        shop_obj=self.pool.get('sale.shop').browse(self.cr,self.uid,shop_id)
        add=shop_obj[0].address_id
        res={}
        res['name']=add
        year_ids=self.pool.get('account.fiscalyear').search(self.cr,self.uid,[('name','=',data['form']['year'])])
        year_obj=self.pool.get('account.fiscalyear').browse(self.cr,self.uid,year_ids[0])
        date=datetime.strptime(year_obj.date_start,'%Y-%m-%d')
        year=date.year
        month_ids=self.pool.get('account.period').search(self.cr,self.uid,[('code','ilike',data['form']['month']+'/'+str(year))])
        month_obj=self.pool.get('account.period').browse(self.cr,self.uid,month_ids[0])
        res['mon_start']=datetime.strptime(month_obj.date_start,'%Y-%m-%d').strftime("%d.%m.%Y")
        res['mon_stop']=datetime.strptime(month_obj.date_stop,'%Y-%m-%d').strftime("%d.%m.%Y")
        return [res]
    
    def get_session_details(self,data):
        print data,'data------------------'
        
        year_ids=self.pool.get('account.fiscalyear').search(self.cr,self.uid,[('name','=',data['form']['year'])])
        year_obj=self.pool.get('account.fiscalyear').browse(self.cr,self.uid,year_ids[0])
        date=datetime.strptime(year_obj.date_start,'%Y-%m-%d')
        year=date.year
        month_ids=self.pool.get('account.period').search(self.cr,self.uid,[('code','ilike',data['form']['month']+'/'+str(year))])
        month_obj=self.pool.get('account.period').browse(self.cr,self.uid,month_ids[0])
        res={}
        mon_start=month_obj.date_start
        mon_stop=month_obj.date_stop
#        pos_id=self.pool.get('pos.session').search(self.cr,self.uid,[('name','=','Main/00003')])
#        print self.pool.get('pos.session').browse(self.cr,self.uid,pos_id[0]).start_at,'date-----------'
#        
        lst=[]
        month=data['form']['month']
        shop=data['form']['pos_shop']
        pos_conf_ids=self.pool.get('pos.config').search(self.cr,self.uid,[('shop_id.name','=',shop)])
#        mstrdate=datetime.strptime(str(year)+'-'+str(month)+'-1','%Y-%m-%d').strftime("%Y-%m-%d")
#        mdate=datetime.strptime(str(year)+'-'+str(month)+'-1','%Y-%m-%d').strftime("%Y-%m-%d")
#        print mdate,'date----------'
        ses_ids=self.pool.get('pos.session').search(self.cr,self.uid,[('config_id','in',pos_conf_ids),('stop_at','>',mon_start),('stop_at','<',mon_stop)])
        print ses_ids,'ses_ids--------'
        ses_objs=self.pool.get('pos.session').browse(self.cr,self.uid,ses_ids)
        cash_ids=self.pool.get('account.bank.statement').search(self.cr,self.uid,[('journal_id.type','=','cash')])
        bank_ids=self.pool.get('account.bank.statement').search(self.cr,self.uid,[('journal_id.type','=','bank')])
        for obj in ses_objs:
            res={}
            res['name']=obj.name
            res['start']=obj.start_at
            res['stop']=obj.stop_at
            stmt_ids=[i.id for i in obj.statement_ids]
            cash=list(set(stmt_ids)&set(cash_ids))
            cash_obj=self.pool.get('account.bank.statement').browse(self.cr,self.uid,cash)
            res['cash']=cash_obj and cash_obj[0].balance_end_real or 0.0
            self.cash_total+=res['cash']
            bank=list(set(stmt_ids)&set(bank_ids))
            bank_obj=self.pool.get('account.bank.statement').browse(self.cr,self.uid,bank)
            res['bank']=bank_obj and bank_obj[0].balance_end_real or 0.0
            self.card_total+=res['bank']
            cash_in_ids=cash_obj and self.pool.get('account.bank.statement.line').search(self.cr,self.uid,[('statement_id','=',cash_obj[0].id),('type','=','general')]) or []
            cash_in_objs=self.pool.get('account.bank.statement.line').browse(self.cr,self.uid,cash_in_ids)
            i,j=0.0,0.0
            for ob in cash_in_objs:
                if ob.amount>0:
                    i+=ob.amount
                else:
                    j+=ob.amount
            bank_in_ids=bank_obj and self.pool.get('account.bank.statement.line').search(self.cr,self.uid,[('statement_id','=',bank_obj[0].id),('type','=','general')]) or []
            bank_in_objs=self.pool.get('account.bank.statement.line').browse(self.cr,self.uid,bank_in_ids)
            for ob in bank_in_objs:
                if ob.amount>0:
                    i+=ob.amount
                else:
                    j+=ob.amount
            res['deposit']=i
            self.deposit_total+=res['deposit']
            res['withdraw']=j
            self.withdraw_total+=res['withdraw']
            lst.append(res)
        return lst
    
    def get_totals(self):
        lst=[]
        res={}
        res['cash_total']=self.cash_total
        res['card_total']=self.card_total
        res['withdraw_total']=self.withdraw_total
        res['deposit_total']=self.deposit_total
        lst.append(res)
        return lst

report_sxw.report_sxw('report.pos_monthly_report', 'monthly.pos.wizard', 'addons/dantunes_pos/report/pos_monthly_report.rml', parser=pos_monthly_report_kt, header=False)
