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


class product_month_kt(report_sxw.rml_parse):


    def __init__(self, cr, uid, name, context=None):
        super(product_month_kt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
           'get_details':self.get_details,
#            'get_data':self.get_data,
#            'get_tot':self.get_tot,
#         'get_money':self.get_money,
#            'get_message_out':self.get_message_out
         'get_cash7':self.get_cash7,
         'get_cash19':self.get_cash19,
         'get_bank7':self.get_bank7,
         'get_bank19':self.get_bank19,
         'get_date':self.get_date,
         'get_addr':self.get_addr,
         'get_name':self.get_name,
         'get_sum':self.get_sum,
         'get_footer':self.get_footer,
            
       })
    g_cash7=0.0
    g_cash19=0.0
    g_bank7=0.0
    g_bank19=0.0
    sum={}
    def get_name(self,data):
      name= to_xml('Ort & Session-Nr')
      
      return name[0:5]+name[9:20]
    
    
    
    def get_addr(self,data):
        res={}
        lst=[]
        shop=data['form']['shops_id']
        pos_shop_id=self.pool.get('sale.shop').search(self.cr,self.uid,[('name','=',shop)])
        
        pos_shop=self.pool.get('sale.shop').browse(self.cr,self.uid,pos_shop_id)
        res['add']=None
        if pos_shop:
        
         pos_add=pos_shop[0].address_id
        res['add']=pos_add
        lst.append(res)
        return lst
    
    def get_footer(self,data):
        res={}
        lst=[]
        mon=data['form']['month_id']
        year=data['form']['year_id']
        month=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
        date=month[int(mon)]+' | MPOS'
        return date
    
    
    def get_details(self,data):
        lst=[]
        year_ids=self.pool.get('account.fiscalyear').search(self.cr,self.uid,[('name','=',data['form']['year_id'])])
        year_obj=self.pool.get('account.fiscalyear').browse(self.cr,self.uid,year_ids[0])
        date=datetime.strptime(year_obj.date_start,'%Y-%m-%d')
        year=date.year
        month_ids=self.pool.get('account.period').search(self.cr,self.uid,[('code','ilike',data['form']['month_id']+'/'+str(year))])
        month_obj=self.pool.get('account.period').browse(self.cr,self.uid,month_ids[0])
        res={}
        mon_start=month_obj.date_start
        mon_stop=month_obj.date_stop
        
        self.sum={'cash7':0.0,'cash19':0.0,'bank7':0.0,'bank19':0.0,'gcpay7':0.0,'gcpay19':0.0,'total_tax':0.0,
                 'cmemo7':0.0,'cmemo19':0.0,'cmemoissue7':0.0,'cmemoissue19':0.0,'tax_return':0.0,'dailytotal':0.0}
        lst=[]
        month=data['form']['month_id']
        shop=data['form']['shops_id']
        pos_conf_ids=self.pool.get('pos.config').search(self.cr,self.uid,[('shop_id.name','=',shop)])
#        mstrdate=datetime.strptime(str(year)+'-'+str(month)+'-1','%Y-%m-%d').strftime("%Y-%m-%d")
#        mdate=datetime.strptime(str(year)+'-'+str(month)+'-1','%Y-%m-%d').strftime("%Y-%m-%d")
        ses_ids=self.pool.get('pos.session').search(self.cr,self.uid,[('config_id','in',pos_conf_ids),('start_at','>=',mon_start),('stop_at','<=',mon_stop)],order='start_at')
        ses_objs=self.pool.get('pos.session').browse(self.cr,self.uid,ses_ids)
        ses_list=[ ]
        for ses in ses_objs:
            ses_list.append(ses.name)
    
        
        for sess in ses_objs:
            pos_ids=self.pool.get('pos.order').search(self.cr,self.uid,[('session_id.name','=',sess.name)])
            pos_objs=self.pool.get('pos.order').browse(self.cr,self.uid,pos_ids)
            cash7percent=0.0
            cash19percent=0.0
            bank7percent=0.0
            bank19percent=0.0
            res={'cash7':0.0,'cash19':0.0,'bank7':0.0,'bank19':0.0,'gcpay7':0.0,'gcpay19':0.0,
                 'cmemo7':0.0,'cmemo19':0.0,'cmemoissue7':0.0,'cmemoissue19':0.0,'tax_return':0.0,'dailytotal':0.0
                 }
            for pos in pos_objs:
              tax_types={}
              tax_totals={}
              amount_totals={}
              total_tax=0.0
              total_amount=0.0
              payment_ratio={'cash':0,'bank':0,'cmemo':0,'gcpay':0}
              payment_amount={'cash':0,'bank':0,'cmemo':0,'gcpay':0}
              if pos.amount_total>0.0:
                  if pos.sale_journal.code.lower()!='gcard':  
                      for line in pos.lines:
                          for tax in line.product_id.taxes_id:
                              if tax_types.has_key(int(tax.amount*100)):
                                  tax_types[int(tax.amount*100)]+=line.qty
                                  tax_totals[int(tax.amount*100)]+=(line.price_subtotal_incl-line.price_subtotal)
                                  amount_totals[int(tax.amount*100)]+=line.price_subtotal_incl
                              else:
                                  tax_types[int(tax.amount*100)]=line.qty
                                  tax_totals[int(tax.amount*100)]=(line.price_subtotal_incl-line.price_subtotal)
                                  amount_totals[int(tax.amount*100)]=line.price_subtotal_incl
                      tax_values=tax_types.keys()
                      for payment in pos.statement_ids:
                          if payment.journal_id.type=='cash':
                              payment_amount['cash']+=payment.amount
                          if payment.journal_id.type=='bank' and payment.journal_id.code.lower() not in ['cmemo','gcpay']:
                              payment_amount['bank']+=payment.amount
                          if payment.journal_id.code.lower()=='cmemo':
                              payment_amount['cmemo']+=payment.amount
                          if payment.journal_id.code.lower()=='gcpay':
                              payment_amount['gcpay']+=payment.amount
                      for payment in pos.statement_ids:
                          if payment.journal_id.type=='cash':
                              payment_ratio['cash']=(payment_amount['cash']/pos.amount_total)*100
                          if payment.journal_id.type=='bank' and payment.journal_id.code.lower() not in ['cmemo','gcpay']:
                              payment_ratio['bank']=(payment_amount['bank']/pos.amount_total)*100
                          if payment.journal_id.code.lower()=='cmemo':
                              payment_ratio['cmemo']=(payment_amount['cmemo']/pos.amount_total)*100
                          if payment.journal_id.code.lower()=='gcpay':
                              payment_ratio['gcpay']=(payment_amount['gcpay']/pos.amount_total)*100
                      act_total_tax=pos.amount_tax
                      self.sum['total_tax']+=pos.amount_tax
                      act_total_amount=pos.amount_total-pos.amount_tax
                      product_ratio={}
                      for tax_val in tax_values:
                          product_ratio[tax_val]=round((tax_totals[tax_val]/pos.amount_total)*100,2)
                      for tax_val in tax_values:
                          total_tax=tax_totals[tax_val]
                          total_amount=amount_totals[tax_val]
                          res['cash'+str(tax_val)]+=(round(total_amount*payment_ratio['cash']/100,2))
                          self.sum['cash'+str(tax_val)]+=(round(total_amount*payment_ratio['cash']/100,2))
                          res['bank'+str(tax_val)]+=(round(total_amount*payment_ratio['bank']/100,2))
                          self.sum['bank'+str(tax_val)]+=(round(total_amount*payment_ratio['bank']/100,2))
                          res['cmemo'+str(tax_val)]+=(round(total_amount*payment_ratio['cmemo']/100,2))
                          self.sum['cmemo'+str(tax_val)]+=(round(total_amount*payment_ratio['cmemo']/100,2))
                          res['gcpay'+str(tax_val)]+=(round(total_amount*payment_ratio['gcpay']/100,2))
                          self.sum['gcpay'+str(tax_val)]+=(round(total_amount*payment_ratio['gcpay']/100,2))
              if pos.amount_total<0.0:
                  if pos.sale_journal.code.lower()!='gcard':   
                      if len(pos.statement_ids)==1 and pos.statement_ids[0].journal_id.code.lower()=='cmemo':
                          for line in pos.lines:
                              for tax in line.product_id.taxes_id:
                                  res['cmemoissue'+str(int(tax.amount*100))]+=line.price_subtotal_incl
                                  self.sum['cmemoissue'+str(int(tax.amount*100))]+=line.price_subtotal_incl
                      else:
                          for line in pos.lines:
                              if line.product_id.default_code and line.product_id.default_code.lower()=='r3tt@xswitz':
                                  res['tax_return']+=line.price_subtotal_incl
                                  self.sum['tax_return']+=line.price_subtotal_incl
            
#            for pos in pos_objs:
#                for line in pos.lines:
##                   print line.price_subtotal, "line--------" 
#                   for tax in line.product_id.taxes_id:
##                     print tax,"taxes----------"  
#                  
#                     if tax.amount == 0.07:                  
#                        if pos.statement_ids[0].journal_id.type =='cash' and pos.statement_ids[0].journal_id.type not in 'bank':
#                           cash7percent+=line.price_subtotal_incl
##                           print 'cash 7 percent----------'
#                        if pos.statement_ids[0].journal_id.type in ['bank','Card']:   
#                             
#                            bank7percent+=line.price_subtotal_incl
##                            print "bank 7 percent------------" 
#                     if tax.amount == 0.19:
#                        if pos.statement_ids[0].journal_id.type=='cash' and pos.statement_ids[0].journal_id.type not in  'bank':
#                            cash19percent+=line.price_subtotal_incl
#                        if pos.statement_ids[0].journal_id.type in ['bank','Card']:     
#                            bank19percent+=line.price_subtotal_incl
#            
            day=datetime.strptime(sess.start_at,'%Y-%m-%d %H:%M:%S').strftime("%A")
            ses_start12 = datetime.strptime(sess.start_at, '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M:%S')
            
            ses_stop12=datetime.strptime(sess.stop_at, '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M:%S')
            dic={"Sunday":"Sonntag","Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch","Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag"}
            
#            if day=="Tuesday":
#                day="Dienstag"
#            if day=="Monday":
#                day="Montag"
#            if day=="Wednesday":
#                day="Mittwoch"    
#            if day=="Thursday":
#                day="Donnerstag"
#            if day=="Friday":
#               day="Freitag"    
#            if day=="Saturday":
#                day="Samstag"
#            if day=="Sunday"    :
#                 day="Sonntag"  

            
            res['ses_name']=sess.name.title()
            res['day']=dic.get(day)
            res['s_strt']=sess.start_at
            res['s_stop']=sess.stop_at
            res['dailytotal']=(res['cash7']+res['cash19']+res['bank7']+res['bank19']+res['cmemo7']+res['cmemo19']+res['gcpay7']+res['gcpay19']+res['cmemoissue7']+res['cmemoissue19'])
            self.sum['dailytotal']+=res['dailytotal']
            lst.append(res)
        return lst
    def get_cash7(self):
        return self.g_cash7
    def get_cash19(self):
        return self.g_cash19
    def get_bank7(self):
        return self.g_bank7
    def get_bank19(self):
        return self.g_bank19
    
    def get_sum(self):
        return [self.sum]
        
    
    def get_date(self,data):
        
        lst=[]
        res={}
        year_ids=self.pool.get('account.fiscalyear').search(self.cr,self.uid,[('name','=',data['form']['year_id'])])
        year_obj=self.pool.get('account.fiscalyear').browse(self.cr,self.uid,year_ids[0])
        
        mon=['','January','February','March','April','May','June','July','August','September','October','Novenber','December']
        mon_id=data['form']['month_id']
     
        int_mon=int(mon_id)
        if year_obj:
         year_str=str(year_obj.code)
        
        
        res['month']=mon[int_mon]+" "+year_str
        lst.append(res)
        return lst

report_sxw.report_sxw('report.Monthly_report', 'pos.order', 'addons/dantunes_pos/report/monthly_report.rml', parser=product_month_kt, header=False)