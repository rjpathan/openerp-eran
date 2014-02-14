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
from math import ceil, floor


from openerp.tools.translate import _


class magento_report_kt(report_sxw.rml_parse):


    def __init__(self, cr, uid, name, context=None):
        super(magento_report_kt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
#            'get_address':self.get_address,
            'get_magento':self.get_magento,
            'get_tot':self.get_tot,
            'get_sub':self.get_sub,
              'get_tax':self.get_tax,          
            'get_add':self.get_add,
            'get_shipping':self.get_shipping,
            'get_shipping_tax':self.get_shipping_tax,
            'get_tax_19':self.get_tax_19,
            'get_tax_7':self.get_tax_7,
            'get_str':self.get_str,
            'get_totalcost':self.get_totalcost,
            'get_footer':self.get_footer,
            
       })

    sub=0.0
    tot=0.0
    add=''
    dat=''
    tax=0.0
    shipping_charges=0.0
    shippingcharges_tax=0.0
    totalcost=0.0
    tax_19 = 0.0
    tax_7 = 0.0
    
    def get_magento(self,data):
        lst=[]
        date=data['form']['date_id']
        day_str=datetime.strptime(date,'%Y-%m-%d').strftime("%Y-%m-%d")
        sale_ids=self.pool.get('account.invoice').search(self.cr,self.uid,[('date_due','=',day_str),('state','=','paid')] )
        sale_obj=self.pool.get('account.invoice').browse(self.cr,self.uid,sale_ids)
        sale_list=[]
        for r in sale_obj:
           if r.origin: 
            sale_list.append(r.origin)
        sale_list=self.pool.get('sale.order').search(self.cr,self.uid,[('name','in',sale_list)])
        sale_dic={}
        for sale_order_obj in self.pool.get('sale.order').browse(self.cr,self.uid,sale_list):
            sale_dic[sale_order_obj.name]=sale_order_obj.magento_id
        for acc in sale_obj:
            if acc.type=='out_refund' or sale_dic[acc.origin]:#start 
              res={}# change on jul 9
              res['amount_tax_19'] = 0
              res['amount_tax_7'] = 0
              res['total_cost']=0.0
              for order_line in acc.invoice_line:
                unit_price = order_line.price_unit
                qty = order_line.quantity
                tot_amount = unit_price * qty
                if acc.type!='out_refund':
                    total_cost_tax=0.0
                    for tax in order_line.product_id.supplier_taxes_id:
                            if tax.price_include:
                                total_cost_tax+=(order_line.product_id.standard_price-(order_line.product_id.standard_price/(1+tax.amount)))
                    res['total_cost']+=(order_line.product_id.standard_price-total_cost_tax)
                    self.totalcost+=(order_line.product_id.standard_price-total_cost_tax)
                discount=round((tot_amount*order_line.discount)/100,2)
                for tax_id in order_line.invoice_line_tax_id:
                   if tax_id.description == 'Magento19.0%':
                       num = tot_amount-discount-order_line.price_subtotal
                       res['amount_tax_19'] += num
                   if tax_id.description == 'Magento7.0%':
                       num = tot_amount-discount-order_line.price_subtotal
                       res['amount_tax_7'] += num 
              if acc.type=='out_refund':
                  self.tax_19 -= res['amount_tax_19']         
                  self.tax_7 -= res['amount_tax_7']
                  res['amount_tax_19']=-res['amount_tax_19']         
                  res['amount_tax_7']=-res['amount_tax_7']
              else:
                  self.tax_19 += res['amount_tax_19']         
                  self.tax_7 += res['amount_tax_7']    
                
              res['origin']=acc.origin
              if  len(acc.origin)>=20:
                           if '-' in acc.origin:
                                  res['origin']= acc.origin.replace('-',': ')
                           if ':' in acc.origin:
                                  res['origin']= acc.origin.replace(':',': ')
              res['partner_id']=acc.partner_id.name
              if acc.type=='out_refund':
                              res['amount_untaxed']=-acc.amount_untaxed
                              self.sub-=acc.amount_untaxed
                              res['amount_total']=-acc.amount_total
                              self.tot-=acc.amount_total
                              res['amount_tax']=-acc.amount_tax
                              self.tax-=acc.amount_tax
              else:      
                          res['amount_untaxed']=acc.amount_untaxed
                          self.sub+=acc.amount_untaxed
                          res['amount_total']=acc.amount_total
                          self.tot+=acc.amount_total
                          res['amount_tax']=acc.amount_tax
                          self.tax+=acc.amount_tax
              res['journal_id']=''
              for pay in acc.payment_ids:
                 res['journal_id']=pay.journal_id.name
              for line in acc.invoice_line:
                      if line.product_id.type=='service' and line.product_id.default_code and line.product_id.default_code.lower()=='shipping':
                          if acc.type=='out_refund':
                                   res['shipping']=-line.price_unit
                                   res['shipping_tax']=-line.price_subtotal
                                   self.shipping_charges+=res['shipping']
                                   self.shippingcharges_tax+=res['shipping_tax']
                          else:
                                   res['shipping']=line.price_unit
                                   res['shipping_tax']=line.price_subtotal
                                   self.shipping_charges+=res['shipping']
                                   self.shippingcharges_tax+=res['shipping_tax']
              lst.append(res)
        return lst
    
    def get_footer(self,data):
        res={}
        lst=[]
        date=data['form']['date_id']
        day_str=datetime.strptime(date,'%Y-%m-%d')
        month=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
        date=str(day_str.day)+' '+month[day_str.month]+' '+str(day_str.year)+' | MD'
        return date
    
    def get_tax_19(self):
        
        return self.tax_19    
        
    def get_tax_7(self):
        return self.tax_7
    
    def get_str(self,a):
        return str(a)
    
    def get_sub(self):
        return self.sub 
    
    def get_tot(self):
        return self.tot  
    
    def get_tax(self):
        return self.tax
    
    def get_shipping(self):
        return self.shipping_charges
    
    def get_shipping_tax(self):
        return self.shippingcharges_tax
    
    def get_totalcost(self):
        return self.totalcost
        
    def get_add(self,data):
        
        date=data['form']['date_id']
        day_str=datetime.strptime(date,'%Y-%m-%d').strftime("%Y-%m-%d")
        dat_ids=self.pool.get('sale.shop').search(self.cr,self.uid,[('name','=','web shop')])
        sal_inv_obj=self.pool.get('sale.shop').browse(self.cr,self.uid,dat_ids)
        lst=[] 
        re={} 
        if sal_inv_obj:   
                 re['add']= sal_inv_obj[0].address_id
        date=datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y')
        day = datetime.strptime(date,'%d-%m-%Y').strftime("%A")
        days ={"Wednesday":'Mittwoch','Monday':'Montag','Tuesday':'Dienstag','Thursday':'Donnerstag','Friday':'Freitag','Saturday':'Samstag','Sunday':'Sonntag'}
        re['dat']= date+'('+days[str(day)]+')'
        lst.append(re)        
        return lst      

report_sxw.report_sxw('report.magento_daily_report', 'sale.order', 'addons/dantunes_pos/report/magento_reprt.rml', parser=magento_report_kt, header=False)

class magento_month_kt(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(magento_month_kt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_addr':self.get_addr,
            'get_cred':self.get_cred,
            'get_bank':self.get_bank,
           'get_sufort':self.get_sufort,
           'get_ccard':self.get_ccard,
            'get_details':self.get_details,
            'get_g_total':self.get_g_total,
            'get_g_total_tax':self.get_g_total_tax,
            'g_salorder':self.g_salorder,
            'get_tax_19':self.get_tax_19,
            'get_tax_7':self.get_tax_7,
            'get_shipping':self.get_shipping,
            'get_shipping_tax':self.get_shipping_tax,
            'get_total_cost':self.get_total_cost,
            'get_str':self.get_str,
            'get_no_return':self.get_no_return,
            'get_footer':self.get_footer,
       })

    g_total=0.0  
    g_total_tax=0.0  
    g_cred=0.0  
    g_bank=0.0  
    g_sft=0.0
    g_ccrd=0.0
    g_sal=0
    tax_19 = 0.0
    tax_7 = 0.0
    shipping_charges = 0.0
    shipping_charges_tax = 0.0
    total_cost=0.0
    no_return=0 # number of credit memos
    
    def get_details(self,data):
        cr=self.cr
        uid=self.uid
        if not data['form']['month_id']:
              raise osv.except_osv(_('Warning!'), _('Bitte den Monat auswählen.'))        
          
        if not data['form']['year_id']:
            raise osv.except_osv(_('Warning!'), _('Bitte das Jahr auswählen.') )   
        
        year_ids=self.pool.get('account.fiscalyear').search(self.cr,self.uid,[('name','=',data['form']['year_id'])])
        year_obj=self.pool.get('account.fiscalyear').browse(self.cr,self.uid,year_ids[0])
        date=datetime.strptime(year_obj.date_start,'%Y-%m-%d')
        year=date.year
        month_ids=self.pool.get('account.period').search(self.cr,self.uid,[('code','ilike',data['form']['month_id']+'/'+str(year))])
        month_obj=self.pool.get('account.period').browse(self.cr,self.uid,month_ids[0])
        res={}
        mon_start=month_obj.date_start
        mon_stop=month_obj.date_stop
        com='%'
        sal_ids=self.pool.get('account.invoice').search(self.cr,self.uid,[('date_due','>=',mon_start),('date_due','<=',mon_stop),('state','=','paid')],order="date_due")
        sal_obj=self.pool.get('account.invoice').browse(self.cr,self.uid,sal_ids)
        
        lst=[]
        dat=[] 
        sale_list=[]
        for r in sal_obj:
           if r.origin: 
            sale_list.append(r.origin)
        sale_list=self.pool.get('sale.order').search(cr,uid,[('name','in',sale_list)])
        sale_dic={}
        for sale_obj in self.pool.get('sale.order').browse(cr,uid,sale_list):
            sale_dic[sale_obj.name]=sale_obj.magento_id
        for r in sal_obj:
           if r.type=='out_refund':
               dat.append(r.date_due)
           else:
               if sale_dic.has_key(r.origin) and sale_dic[r.origin]>0: 
                   dat.append(r.date_due)
        uni_dat=sorted(list(set(dat)))
            
        for rec in uni_dat:
             floag=False
             cred=0.0   
             bank=0.0
             sft=0.0
             crdc=0.0 
             cred_return=0.0   
             bank_return=0.0
             sft_return=0.0
             crdc_return=0.0 
             dat_ids=self.pool.get('account.invoice').search(self.cr,self.uid,[('date_due','=',rec),('state','=','paid')])
             sal_inv_obj=self.pool.get('account.invoice').browse(self.cr,self.uid,dat_ids)
             day_tax_19 = 0.0# added start
             day_tax_7 = 0.0
             day_shipping = 0.0
             day_shipping_tax=0.0
             day_tax_19_return = 0.0# added start
             day_tax_7_return = 0.0
             day_shipping_return = 0.0
             day_shipping_tax_return = 0.0
             total_cost=0.0
             invoices = []
             noreturn=0
             noinvoice=0
#             for sale_obj in sal_inv_obj:
#                   for inv in sale_obj.invoice_ids:
#                           if inv.state=='paid':
#                            invoices.append(inv)
             for sal in sal_inv_obj:
                 for order_line in sal.invoice_line:
                    if order_line.product_id.type == 'service' and order_line.product_id.default_code and order_line.product_id.default_code.lower()=='shipping':#this is to get shipping charges
                        if sal.type=='out_refund':
                           day_shipping_return += order_line.price_unit
                           day_shipping_tax_return += order_line.price_subtotal
                        else:
                           day_shipping += order_line.price_unit
                           day_shipping_tax += order_line.price_subtotal
                    if sal.type!='out_refund':
                        total_cost_tax=0.0
                        for tax in order_line.product_id.supplier_taxes_id:
                            if tax.price_include:
                                total_cost_tax+=(order_line.product_id.standard_price-(order_line.product_id.standard_price/(1+tax.amount)))
                        total_cost+=(order_line.product_id.standard_price-total_cost_tax)
                    unit_price = order_line.price_unit
                    qty = order_line.quantity
                    tot_amount = unit_price * qty
                    discount=round((tot_amount*order_line.discount)/100,2)
                    for tax_id in order_line.invoice_line_tax_id:
                       if tax_id.description == 'Magento19.0%':
                           num = tot_amount-discount-order_line.price_subtotal
                           if sal.type=='out_refund':
                                  day_tax_19_return += num  
                           else:
                                   day_tax_19 += num    
                           
                       if tax_id.description == 'Magento7.0%':
                           num = tot_amount-discount-order_line.price_subtotal
                           if sal.type=='out_refund': 
                                  day_tax_7_return += num
                           else:
                                  day_tax_7 += num
                 
                 #end
                 for pay in sal.payment_ids:
                         if sal.type=='out_refund':
                                  floag=True
                                  noreturn +=1
                         else:
                                noinvoice+=1
                         if pay.journal_id.code.lower() =='paypa':
                              if sal.type=='out_refund':
                                 cred_return += pay.debit
                              else:
                                   cred += pay.credit 
                               
                         if pay.journal_id.code.lower() =='vorka': 
                              if sal.type=='out_refund':
                                    bank_return += pay.debit
                              else:
                                    bank += pay.credit     
                               
                         if pay.journal_id.code.lower() =='sofrt':
                             if sal.type=='out_refund':
                                    sft_return +=pay.debit
                             else:
                                      sft +=pay.credit
                         if pay.journal_id.code.lower() =='krt3':
                              if sal.type=='out_refund':
                                    crdc_return +=pay.debit    
                              else:
                                     crdc +=pay.credit   
             self.tax_19 += day_tax_19-day_tax_19_return    #added     
             self.tax_7 += day_tax_7-day_tax_7_return #added
             self.shipping_charges+= day_shipping-day_shipping_return
             self.shipping_charges_tax+= day_shipping_tax-day_shipping_tax_return
             res={}
             res_return={}
             date=datetime.strptime(rec, '%Y-%m-%d').strftime('%d-%m-%Y')
             
             res['tax_19'] = day_tax_19#added
             res['tax_7'] = day_tax_7#added
             res['shipping'] = day_shipping
             res['shipping_tax'] = day_shipping_tax
             res['date_order']=date
             
             res_return['tax_19'] = -day_tax_19_return#added
             res_return['tax_7'] = -day_tax_7_return#added
             res_return['shipping'] = -day_shipping_return
             res_return['shipping_tax'] = -day_shipping_tax_return
             res_return['date_order']=date

             res['pay']=cred
             res_return['pay']=-cred_return
             self.g_cred+=cred-cred_return
             res['vor']=bank
             res_return['vor']=-bank_return
             self.g_bank+=bank-bank_return
             res['sft']=sft
             res_return['sft']=-sft_return
             self.g_sft+=sft-sft_return
             res['crc']=crdc
             res_return['crc']=-crdc_return 
             self.g_ccrd+=crdc-crdc_return 
             res['nos']=noinvoice
             res_return['nos']=noreturn
             self.g_sal+=noinvoice
             res['total_tax']=cred+bank+sft+crdc-res['tax_19']-res['tax_7']
             res['total']=cred+bank+sft+crdc
             res_return['total_tax']=-(cred_return+bank_return+sft_return+crdc_return)
             res_return['total']=-(cred_return+bank_return+sft_return+crdc_return+res_return['tax_19']+res_return['tax_7'])
             self.g_total +=(cred+bank+sft+crdc)-(cred_return+bank_return+sft_return+crdc_return)
             self.g_total_tax +=res['total_tax']+res_return['total_tax']
             self.no_return +=noreturn
             res['total_cost']=total_cost
             self.total_cost+=total_cost
             res_return['total_cost']=0.0
             if noinvoice:
                 lst.append(res)
             if floag:
                  lst.append(res_return)
        return lst                     
                        
    def get_footer(self,data):
        res={}
        lst=[]
        mon=data['form']['month_id']
        month=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
        date=month[int(mon)]+' | MM'
        return date
    
    def get_no_return(self):
        return str(self.no_return)
    
    def get_tax_19(self):
        return self.tax_19
    
    def get_tax_7(self):
        return self.tax_7
    def get_shipping(self):
        return self.shipping_charges
    
    def get_shipping_tax(self):
        return self.shipping_charges_tax
    
    def get_total_cost(self):
        return self.total_cost    
    
    def get_cred(self):
        return self.g_cred
    
    def get_str(self,a):
        return str(a)
    
    def get_bank(self):  
        return self.g_bank
    
    def get_sufort(self):
        return self.g_sft  
      
    def get_ccard(self):
        return self.g_ccrd   
       
    def get_g_total(self):
        return self.g_total
    
    def get_g_total_tax(self):
        return self.g_total_tax
        
    def g_salorder(self):    
        return self.g_sal
    
    def get_addr(self,data):
         lst=[]        
         dat_ids=self.pool.get('sale.order').search(self.cr,self.uid,[('shop_id.name','=','web shop')])
         sal_inv_obj=self.pool.get('sale.order').browse(self.cr,self.uid,dat_ids)
         res={ }
         if sal_inv_obj:
              res['add']=sal_inv_obj[0].shop_id.address_id
              lst.append(res)
         return lst
     
report_sxw.report_sxw('report.magento_monthly_report', 'sale.order', 'addons/dantunes_pos/report/mag_montly_rpt.rml', parser=magento_month_kt, header=False)
