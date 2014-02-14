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

from openerp.tools.translate import _


class product_report_kt(report_sxw.rml_parse):


    def __init__(self, cr, uid, name, context=None):
        super(product_report_kt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_data':self.get_data,
#            'get_tot':self.get_tot,
            'get_footer':self.get_footer, 
            'get_addr':self.get_addr
       })
    def get_addr(self,data):
        res={}
        lst=[]
        date=data['form']['date_id']
        day_str=datetime.strptime(date,'%Y-%m-%d').strftime("%Y-%m-%d %H:%M:%S")
        day_end=datetime.strptime(date+' 23:59:59','%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M:%S")
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
        date=data['form']['date_id']
        day_str=datetime.strptime(date,'%Y-%m-%d')
        month=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
        date=str(day_str.day)+' '+month[day_str.month]+' '+str(day_str.year)+' | DPOS'
        return date
   
    banktotal=0.00
    def get_data(self,data):  
       
        lst=[]
        date=data['form']['date_id']
        day_str=datetime.strptime(date,'%Y-%m-%d').strftime("%Y-%m-%d %H:%M:%S")
        day_end=datetime.strptime(date+' 23:59:59','%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M:%S")
        shop=data['form']['shops_id']
        pos_conf_ids=self.pool.get('pos.config').search(self.cr,self.uid,[('shop_id.name','=',shop)])
        sess_ids=self.pool.get('pos.session').search(self.cr,self.uid,[('config_id','in',pos_conf_ids),('start_at','>',day_str),('stop_at','<',day_end)])
        sess_objs=self.pool.get('pos.session').browse(self.cr,self.uid,sess_ids)
        if not sess_objs:
              raise osv.except_osv(_('Warning!'), _('Es gibt keine Sitzung zu diesem Zeitpunkt, wähle bitte ein anderes Datum.'))     
        
        for sess in sess_objs:
            res={}
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
            
            res['day']= dic.get(day) 
            res['sess_name']=sess.name.title()
            res['user']=sess.user_id.name
            res['opening']=sess.cash_register_balance_start
            res['closing']=sess.cash_register_balance_end_real
            res['strt']=sess.start_at
            res['end']=sess.stop_at
            res['s_id']=sess.id
            res['money_in_out']=[]
            res['message_in']=[]
            res['message_out']=[]  
         
            in_amnt=0.00
            ot_amnt=0.00
            in_count=0
            ot_count=0
            for mon in sess.statement_ids:
              for line  in mon.line_ids:
               if  line.type == 'general' and line.amount>0:
                   val={}
                   val['msg_in']=line.name
                   val['amt_in']=line.amount
                   if not val['msg_in']=='Point of Sale Profit':
                          in_count+=1
                          res['message_in'].append(val)
                          in_amnt+=line.amount
               if  line.type == 'general' and line.amount<0:   
                    val={}
                    val['msg_out']=line.name
                    val['amt_out']=-(line.amount)
                    if not val['msg_out']=='Point of Sale Loss':
                          ot_count+=1 
                          res['message_out'].append(val)
                          ot_amnt+=line.amount
                   
            val={}
            val['in_amnt']=in_amnt
            val['in_cnt']=in_count
            val['ot_amnt']=ot_amnt
            val['ot_cnt']=ot_count       
            res['money_in_out'].append(val)
            
#           -----------Modified by Kiran.P-----------
            res['cash19']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['cash7']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['bank7']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['bank19']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['cmemo7']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['cmemo19']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['cmemoissue7']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['cmemoissue19']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['gcpay7']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['gcpay19']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['refund19']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['refund7']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['giftcard_cash']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['giftcard_bank']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['giftcard_19r']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['giftcard_7r']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['cashtotal']=0.0
            res['refundtotal']=0.0
            res['cmemoissuetotal']=0.0
            res['banktotal']=0.0
            res['cmemoreedemsum']=0.0
            res['dailytotal']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['tax_return']=[{'qty':0,'net':0.0,'tax':0.0,'gross':0.0}]
            res['gcardissuecash']=[]
            res['gcardissuebank']=[]
            res['gcardredeem']=[]
            pos_ids=self.pool.get('pos.order').search(self.cr,self.uid,[('session_id.name','=',sess.name)])
            pos_objs=self.pool.get('pos.order').browse(self.cr,self.uid,pos_ids)
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
                                  amount_totals[int(tax.amount*100)]+=line.price_subtotal
                              else:
                                  tax_types[int(tax.amount*100)]=line.qty
                                  tax_totals[int(tax.amount*100)]=(line.price_subtotal_incl-line.price_subtotal)
                                  amount_totals[int(tax.amount*100)]=line.price_subtotal
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
                      act_total_amount=pos.amount_total-pos.amount_tax
                      product_ratio={}
                      for tax_val in tax_values:
                          product_ratio[tax_val]=round((tax_totals[tax_val]/pos.amount_total)*100,2)
                      for tax_val in tax_values:
                          total_tax=tax_totals[tax_val]
                          total_amount=amount_totals[tax_val]
                          res['cash'+str(tax_val)][0]['qty']+=(round(total_amount*payment_ratio['cash']/100,2)>0.0 and tax_types[tax_val] or 0.0)
                          res['cash'+str(tax_val)][0]['net']+=round(total_amount*payment_ratio['cash']/100,2)
                          res['cash'+str(tax_val)][0]['tax']+=round(total_tax*payment_ratio['cash']/100,2)
                          res['cash'+str(tax_val)][0]['gross']+=(round(total_amount*payment_ratio['cash']/100,2)+round(total_tax*payment_ratio['cash']/100,2))
                          res['bank'+str(tax_val)][0]['qty']+=(round(total_amount*payment_ratio['bank']/100,2)>0.0 and tax_types[tax_val] or 0.0)
                          res['bank'+str(tax_val)][0]['net']+=round(total_amount*payment_ratio['bank']/100,2)
                          res['bank'+str(tax_val)][0]['tax']+=round(total_tax*payment_ratio['bank']/100,2)
                          res['bank'+str(tax_val)][0]['gross']+=(round(total_amount*payment_ratio['bank']/100,2)+round(total_tax*payment_ratio['bank']/100,2))
                          res['cmemo'+str(tax_val)][0]['qty']+=(round(total_amount*payment_ratio['cmemo']/100,2)>0.0 and tax_types[tax_val] or 0.0)
                          res['cmemo'+str(tax_val)][0]['net']+=round(total_amount*payment_ratio['cmemo']/100,2)
                          res['cmemo'+str(tax_val)][0]['tax']+=round(total_tax*payment_ratio['cmemo']/100,2)
                          res['cmemo'+str(tax_val)][0]['gross']+=(round(total_amount*payment_ratio['cmemo']/100,2)+round(total_tax*payment_ratio['cmemo']/100,2))
                          res['gcpay'+str(tax_val)][0]['qty']+=(round(total_amount*payment_ratio['gcpay']/100,2)>0.0 and tax_types[tax_val] or 0.0)
                          res['gcpay'+str(tax_val)][0]['net']+=round(total_amount*payment_ratio['gcpay']/100,2)
                          res['gcpay'+str(tax_val)][0]['tax']+=round(total_tax*payment_ratio['gcpay']/100,2)
                          res['gcpay'+str(tax_val)][0]['gross']+=(round(total_amount*payment_ratio['gcpay']/100,2)+round(total_tax*payment_ratio['gcpay']/100,2))
                  else:
                      if len(pos.statement_ids)==1:
                          if pos.statement_ids[0].journal_id.type=='cash':
                              res['giftcard_cash'][0]['qty']+=1
                              res['giftcard_cash'][0]['gross']+=pos.statement_ids[0].amount
                              for line in pos.lines:
                                  flag=False
                                  for card_pro in res['gcardissuecash']:
                                      if card_pro['name']==line.product_id.name:
                                          card_pro['qty']+=1
                                          card_pro['gross']+=line.price_subtotal
                                          flag=True
                                  if flag==False:
                                      res['gcardissuecash'].append({'name':line.product_id.name,'qty':line.qty,'gross':line.price_subtotal})
                          else:
                              res['giftcard_bank'][0]['qty']+=1
                              res['giftcard_bank'][0]['gross']+=pos.statement_ids[0].amount
                              for line in pos.lines:
                                  flag=False
                                  for card_pro in res['gcardissuebank']:
                                      if card_pro['name']==line.product_id.name:
                                          card_pro['qty']+=1
                                          card_pro['gross']+=line.price_subtotal
                                          flag=True
                                  if flag==False:
                                      res['gcardissuebank'].append({'name':line.product_id.name,'qty':line.qty,'gross':line.price_subtotal})
                      else:
                          res['giftcard_bank'][0]['qty']+=1
                          res['giftcard_bank'][0]['gross']+=pos.amount_total
                          for line in pos.lines:
                                  flag=False
                                  for card_pro in res['gcardissuebank']:
                                      if card_pro['name']==line.product_id.name:
                                          card_pro['qty']+=1
                                          card_pro['gross']+=line.price_subtotal
                                          flag=True
                                  if flag==False:
                                      res['gcardissuebank'].append({'name':line.product_id.name,'qty':line.qty,'gross':line.price_subtotal})
                      
                  
#                  for line in pos.lines:
#                    for tax in line.product_id.taxes_id:
#                      if tax.amount == 0.07:                  
#                        if pos.statement_ids[0].journal_id.type =='cash' and pos.statement_ids[0].journal_id.type not in 'bank':
#                          cash7p+=line.qty
#                          cash7pprice+=line.price_subtotal
#                          cash7tax+=line.price_subtotal_incl-line.price_subtotal
#                        if pos.statement_ids[0].journal_id.type == 'bank':     
#                          bank7qty+=line.qty
#                          bank7price+=line.price_subtotal
#                          bank7tax+=line.price_subtotal_incl-line.price_subtotal
#                      if tax.amount == 0.19:
#                        if pos.statement_ids[0].journal_id.type=='cash' and pos.statement_ids[0].journal_id.type not in  'bank':
#                          c9qty+=line.qty
#                          c9p+=line.price_subtotal
#                          c9tax+=line.price_subtotal_incl-line.price_subtotal
#           
#                        if pos.statement_ids[0].journal_id.type == 'bank':     
#                          b9qty+=line.qty
#                          b9price+=line.price_subtotal
#                          b9tax+=line.price_subtotal_incl-line.price_subtotal
              if pos.amount_total<0.0:
                  if pos.sale_journal.code.lower()!='gcard':   
                      if len(pos.statement_ids)==1 and pos.statement_ids[0].journal_id.code.lower()=='cmemo':
                          for line in pos.lines:
                              for tax in line.product_id.taxes_id:
                                  res['cmemoissue'+str(int(tax.amount*100))][0]['qty']+=line.qty
                                  res['cmemoissue'+str(int(tax.amount*100))][0]['net']+=line.price_subtotal
                                  res['cmemoissue'+str(int(tax.amount*100))][0]['tax']+=line.price_subtotal_incl-line.price_subtotal
                                  res['cmemoissue'+str(int(tax.amount*100))][0]['gross']+=line.price_subtotal_incl
#                                  res['cmemoissuetotal']+=line.price_subtotal_incl
                      else:
                          for line in pos.lines:
                              for tax in line.product_id.taxes_id:
                                  res['refund'+str(int(tax.amount*100))][0]['qty']+=line.qty
                                  res['refund'+str(int(tax.amount*100))][0]['net']+=line.price_subtotal
                                  res['refund'+str(int(tax.amount*100))][0]['tax']+=line.price_subtotal_incl-line.price_subtotal
                                  res['refund'+str(int(tax.amount*100))][0]['gross']+=line.price_subtotal_incl
                              if line.product_id.default_code and line.product_id.default_code.lower()=='r3tt@xswitz':
                                  res['tax_return'][0]['qty']+=1
                                  res['tax_return'][0]['gross']+=line.price_subtotal_incl
                  else:
                      for line in pos.lines:
                          flag=False
                          for card_pro in res['gcardredeem']:
                              if card_pro['name']==line.product_id.name:
                                  card_pro['qty']+=1
                                  card_pro['gross']+=line.price_subtotal
                                  flag=True
                          if flag==False:
                              res['gcardredeem'].append({'name':line.product_id.name,'qty':1,'gross':line.price_subtotal})        
#                      for line in pos.lines:
#                        for tax in line.product_id.taxes_id:
#                          if tax.amount == 0.07:                  
#                            if pos.statement_ids[0].journal_id.type =='cash' and pos.statement_ids[0].journal_id.type not in 'bank':
#                              refund7p+=line.qty
#                              refund7pprice+=line.price_subtotal
#                              refund7tax+=line.price_subtotal_incl-line.price_subtotal
#                          if tax.amount == 0.19:
#                            if pos.statement_ids[0].journal_id.type=='cash' and pos.statement_ids[0].journal_id.type not in  'bank':
#                              refund9qty+=line.qty
#                              refund9p+=line.price_subtotal
#                              refund9tax+=line.price_subtotal_incl-line.price_subtotal
            res['banktotal']+=(res['bank7'][0]['gross']+res['bank19'][0]['gross'])
            res['cashtotal']+=(res['cash7'][0]['gross']+res['cash19'][0]['gross'])
            res['refundtotal']+=(res['refund7'][0]['gross']+res['refund19'][0]['gross'])
            res['cmemoreedemsum']+=(res['cmemo7'][0]['gross']+res['cmemo19'][0]['gross'])
            res['cmemoissuetotal']+=(res['cmemoissue7'][0]['gross']+res['cmemoissue19'][0]['gross'])
            res['dailytotal'][0]['net']=res['bank7'][0]['net']+res['bank19'][0]['net']+res['cash7'][0]['net']+res['cash19'][0]['net']+res['refund7'][0]['net']+res['refund19'][0]['net']+\
                                        res['gcpay7'][0]['net']+res['gcpay19'][0]['net']+res['cmemoissue7'][0]['net']+res['cmemoissue19'][0]['net']+res['cmemo7'][0]['net']+res['cmemo19'][0]['net']
            res['dailytotal'][0]['tax']=res['bank7'][0]['tax']+res['bank19'][0]['tax']+res['cash7'][0]['tax']+res['cash19'][0]['tax']+res['refund7'][0]['tax']+res['refund19'][0]['tax']+\
                                        res['gcpay7'][0]['tax']+res['gcpay19'][0]['tax']+res['cmemoissue7'][0]['tax']+res['cmemoissue19'][0]['tax']+res['cmemo7'][0]['tax']+res['cmemo19'][0]['tax']
            res['dailytotal'][0]['gross']=res['bank7'][0]['gross']+res['bank19'][0]['gross']+res['cash7'][0]['gross']+res['cash19'][0]['gross']+res['refund7'][0]['gross']+res['refund19'][0]['gross']+\
                                        res['gcpay7'][0]['gross']+res['gcpay19'][0]['gross']+res['cmemoissue7'][0]['gross']+res['cmemoissue19'][0]['gross']+res['cmemo7'][0]['gross']+res['cmemo19'][0]['gross']
            res['closing']=res['opening']+res['cashtotal']+res['refundtotal']+res['money_in_out'][0]['in_amnt']+res['money_in_out'][0]['ot_amnt']+res['giftcard_cash'][0]['gross']+res['tax_return'][0]['gross']
            lst.append(res)
       
        return lst
    

report_sxw.report_sxw('report.Daily_report', 'pos.order', 'addons/dantunes_pos/report/daily_rpt.rml', parser=product_report_kt, header=False)
