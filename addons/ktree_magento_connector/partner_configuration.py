from osv import fields,osv
from mx import DateTime
import netsvc
import tools
import pooler
import time
import datetime
import math
import os
import traceback
from pprint import pprint
import base64, urllib
from openerp.tools.translate import _
#inherit magento_configuration class to add partner import and export functions
class magento_configuration(osv.osv):
    _inherit = 'magento.configuration'
    # This function is used to export Customer from openerp to Magento
    def export_customers(self,cr,uid):
        total_no_of_records=0
       
            # magneto object through which connecting openerp with defined magneto configuration start
        magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
        [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
        if not status:
             raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                    please check the url,username and password") )  
             return -1
            #end
        try:
            #searching all customer from openerp
            customer_ids = self.pool.get('res.partner').search(cr, uid, [('export_magento','=',True),('modified', '=', 'True'),('parent_id','=', None)])
            child_customer_ids = self.pool.get('res.partner').search(cr, uid, [('export_magento','=',True),('modified', '=', 'True'),('parent_id','<>', None)])
           
            for child_obj in self.pool.get('res.partner').browse(cr, uid, child_customer_ids):
                customer_ids.append(child_obj.parent_id.id)
            customer_ids = list(set(customer_ids))    
            #making customers object for  searched customer
            customers = self.pool.get('res.partner').browse(cr, uid, customer_ids)
            all_customer_id=[]
            for cus in customers:
                if cus['customer'] and cus.magento_id != -1:
                     all_customer_id.append(str(cus.magento_id))
            try:          
                 #API to get customer information for all customer_id at a time 
                 all_info_customers = [server.call(session, 'customapi_customer.itemslist' , [all_customer_id])][0];  
            
            except:
                 all_info_customers=[]  
                      
            for cus in customers:
                name_list = cus['name'].split()
                first_name = name_list[0]
                lastname =  ' '.join([x for x in name_list[1:]])
                customer_data = {
                                 'email'      : cus['email'],
                                 'group_id'   : cus['group_id'].magento_id or False,
                                 'created_at' : cus['created_at'],
                                 'website_id' : cus['website_id'],
                                 'firstname' : first_name,
                                 'lastname': lastname,
                                 }
                
                #checking availability of customer in magneto
                available=False
                if cus.magento_id !=-1:
                    info_customer = [customer for customer in all_info_customers if int(cus.magento_id)==int(customer['customer_id'])]
                    if info_customer:
                       available=True
                #creating new customer in magneto 
                if ((cus.magento_id == -1) or (not available)):
                         try:
                                if cus['export_magento'] and cus['customer'] and cus['email']:
                                    magento_id = server.call(session, 'customer.create', [customer_data]);
                                    self.pool.get('res.partner').write(cr, uid,cus.id, {'magento_id': magento_id,'modified':False})
                                    if magento_id:
                                       total_no_of_records+=1  
                                    cust_add_ids = self.pool.get('res.partner').search(cr, uid, [('parent_id','=',cus.id)])
                                    cust_address = self.pool.get('res.partner').browse(cr, uid, cust_add_ids)
                                    for cust_add in cust_address:
                                        name_list1 = cust_add['name'] and cust_add['name'].split() or cus['name'].split()
                                        first_name1 = name_list1[0]
                                        lastname1 =  ' '.join([x for x in name_list1[1:]])
                                        street=cust_add['street'] 
                                        if cust_add['street2']:
                                            street=street+str(' ') + cust_add['street2']
                                        cus_address_data = { 
                                                       'city'        : cust_add['city'],
                                                       'firstname'   : first_name1,
                                                       'lastname'    : lastname1 ,
                                                       'country_id'  : cust_add['country_id'].code,
                                                       'telephone'   : cust_add['phone'],
                                                       'street'      : street,
                                                       'postcode'    : cust_add['zip'],
                                                       'type'        : cust_add['type'],
                                                       'customer_id'         : cus.magento_id,
                                                          }
                                        if cust_add['type'] == 'delivery':
                                            cus_address_data['is_default_shipping'] = True
                                        else:
                                            cus_address_data['is_default_shipping'] = False    
                                        if  cust_add['type'] == 'invoice': 
                                              cus_address_data['is_default_billing'] = True
                                        else:
                                             cus_address_data['is_default_billing'] = False 
                                        #inserting customer address in magneto for created  in magneto
                                        #street,city,zip,phone,country_id are compulsory fields in magneto
                                        if  cust_add['street'] and cust_add['city'] and   cust_add['country_id'] and cust_add['zip'] and cust_add['phone'] :
                                            magento_add_id = server.call(session, 'customer_address.create', [str(magento_id),cus_address_data]); 
                                            self.pool.get('res.partner').write(cr, uid,cust_add.id, {'magento_address_id': magento_add_id,'modified':False,'export_magento':True})   
                         except :
                              pass
                else:
                  try:
                    if available and cus['email']:
                        #updating customer in magneto 
                        server.call(session, 'customer.update', [ cus.magento_id, customer_data]);
                        self.pool.get('res.partner').write(cr, uid,cus.id,{'modified':False})
                        total_no_of_records +=1
                        #updating customer address in magneto for specified customer
                        cust_add_ids = self.pool.get('res.partner').search(cr, uid, [('parent_id','=',cus.id)])
                        cust_address = self.pool.get('res.partner').browse(cr, uid, cust_add_ids)
                        for cust_add in cust_address:
                            name_list1 = cust_add['name'] and cust_add['name'].split() or cus['name'].split()
                            first_name1 = name_list1[0]
                            lastname1 =  ' '.join([x for x in name_list1[1:]])
                            street=cust_add['street'] 
                            if cust_add['street2']:
                                street=street+str(' ') + cust_add['street2']
                            cus_address_data = { 
                                           'city'       : cust_add['city'],
                                           'firstname'  : first_name1,
                                           'lastname'   : lastname1 ,
                                           'country_id' : cust_add['country_id'].code,
                                           'telephone'  : cust_add['phone'],
                                           'street'     : street,
                                           'postcode'   : cust_add['zip'],
                                           'type'       : cust_add['type'],
                                          
                                         }
                            if cust_add['type'] == 'delivery':
                                cus_address_data['is_default_shipping'] = True
                            else:
                                cus_address_data['is_default_shipping'] = False    
                            if  cust_add['type'] == 'invoice': 
                                cus_address_data['is_default_billing'] = True
                            else:
                                cus_address_data['is_default_billing'] = False
                            if cust_add['magento_id'] and int(cust_add['magento_id']) >= 1:
                                #API for customer address updation in magneto
                                server.call(session, 'customer_address.update', [cust_add['magento_id'], cus_address_data]); 
                            elif cust_add['street'] and cust_add['city'] and   cust_add['country_id'] and cust_add['zip'] and cust_add['phone'] :  
                                #API for customer address creation in magneto
                                magento_add_id = server.call(session, 'customer_address.create', [str(cus.magento_id),cus_address_data]);
                                self.pool.get('res.partner').write(cr, uid,cust_add.id, {'magento_address_id': magento_add_id,'modified':False,'export_magento':True})
                  except :
                        pass
                                                       
            return total_no_of_records
        except:
            return -1
     
    #update the customer while sale order importing based on ('name','street','zip','country_id','city','phone')
    def update_customer(self, cr, uid, infos):
        try:
            infos['customer_is_guest']
        except:
            infos['customer_is_guest'] = '0'
        if infos['customer_is_guest'] == '1':
            infos['customer_id'] = '0'
        email=''
        if infos.has_key('email') and infos['email']:
            email=infos['email']
        created_at=False
        try:
             try:
                if infos['shipping_address']['customer_id'] and infos['shipping_address']['customer_id'] == infos['billing_address']['customer_id'] :
                      infos['customer_id'] = infos['shipping_address']['customer_id']
             except:
                 try:         
                       if infos['shipping_address']['customer_id']  :
                           infos['customer_id'] =infos['shipping_address']['customer_id']
                 except:
                        if infos['billing_address']['customer_id'] :
                                   infos['customer_id'] =infos['billing_address']['customer_id']
        except:
                  infos['customer_id']=infos['customer_id']              
        if infos.has_key('created_at') and infos['created_at']:
            created_at=infos['created_at']
        erp_customer = {   
                        'magento_id' : infos['customer_id'],
                        'export_magento':True,
                        'email' : email,
                        'created_at' : created_at,
                        'is_company':True,
                        'customer'   : True,
                        'supplier'   : False}
        if infos.has_key('firstname') and infos['firstname'] and infos.has_key('lastname') and infos['lastname']:
            erp_customer['name'] = infos['firstname']+ ' ' + infos['lastname']
        elif infos.has_key('firstname') and infos['firstname']:
            erp_customer['name'] = infos['firstname']
        elif infos.has_key('lastname') and infos['lastname']:
            erp_customer['name'] = infos['lastname']
        else:
              erp_customer['name'] = infos['billing_address']['firstname']+' '+ infos['billing_address']['lastname']   #Dummy
#            erp_customer['name'] = 'Default Customer'     
        new_shipping_address = infos['shipping_address']
        new_billing_address = infos['billing_address']
        if not erp_customer['magento_id']:
            pass #print infos
        # check to see if customer is guest, if so always create
        if int(erp_customer['magento_id'])==0:
            cust_ids = self.pool.get('res.partner').search(cr, uid, [('name', '=', erp_customer['name']),('parent_id','=',False)])
        else:
            cust_ids = self.pool.get('res.partner').search(cr, uid, [('magento_id', '=', int(erp_customer['magento_id']))])
        if cust_ids == []:
            cust_ids = [self.pool.get('res.partner').create(cr, uid, erp_customer)]
        else:
            erp_customer['modified']=False
            self.pool.get('res.partner').write(cr, uid, [cust_ids[0]], erp_customer  )
        if cust_ids == []:
            return [None , None, None]
        erp_contact_billing={}
        erp_contact_shipping={}
        # Billing country start
        if new_billing_address:
            try:
                new_billing_address_country = self.pool.get('res.country').name_search(cr, uid, new_billing_address['country_id'])[0][0]
            except:
                new_country = { 'name': new_billing_address['country_id'],
                                'code': new_billing_address['country_id']} 
                new_billing_address_country = self.pool.get('res.country').create(cr, uid, new_country)
            state_id=False
            if infos.has_key('region') and infos['region']:
                try:
                    state_id = self.pool.get('res.country.state').name_search(cr, uid, new_billing_address['region'])[0][0]
                except:
                    state_new = { 'name': new_billing_address['region'],
                                  'code': new_billing_address['region'],
                                  'country_id': new_billing_address_country
                                }
                    state_id = self.pool.get('res.country.state').create(cr, uid, state_new)
            fax=''
            if new_billing_address.has_key('fax') and new_billing_address['fax']:
                fax=new_billing_address['fax']
            postcode=''
            if new_billing_address.has_key('postcode') and new_billing_address['postcode']:
                postcode=new_billing_address['postcode'] 
            city=''
            if new_billing_address.has_key('city') and new_billing_address['city']:
                city=new_billing_address['city'] 
            telephone=''
            if new_billing_address.has_key('telephone') and new_billing_address['telephone']:
                telephone=new_billing_address['telephone']             
            erp_contact_billing = { 
                                   'parent_id'  : cust_ids[0],
                                  'type'          : 'invoice',
                                  'name'          : new_billing_address['firstname'] + ' ' + new_billing_address['lastname'],
                                  'street'        : new_billing_address['street'],
                                  'zip'           : postcode,
                                  'city'          : city,
                                  'state_id'      :state_id,
                                   'email'        : email,
                                   'fax'          :fax,
                                  'country_id'    :new_billing_address_country,
                                  'phone'         :telephone,
                                  'use_parent_address':False,
                                  }
        #End
        #Shipping country start
        if new_shipping_address:
            try:
                new_shipping_address_country = self.pool.get('res.country').name_search(cr, uid, new_shipping_address['country_id'])[0][0]
            except:
                new_country = { 'name': new_shipping_address['country_id'],
                                'code': new_shipping_address['country_id']}
                new_shipping_address_country = self.pool.get('res.country').create(cr, uid, new_country)    
                                   
            state_id=False
            if infos.has_key('region') and infos['region']:
                try:
                    state_id = self.pool.get('res.country.state').name_search(cr, uid, new_shipping_address['region'])[0][0]
                except:
                    state_new = { 'name': new_shipping_address['region'],
                                    'code': new_shipping_address['region'],
                                    'country_id':new_shipping_address_country}
                    state_id = self.pool.get('res.country.state').create(cr, uid, state_new)
            fax=''
            if new_shipping_address.has_key('fax') and new_shipping_address['fax']:
                fax=new_shipping_address['fax']
            postcode=''
            if new_shipping_address.has_key('postcode') and new_shipping_address['postcode']:
                postcode=new_shipping_address['postcode'] 
            city=''
            if new_shipping_address.has_key('city') and new_shipping_address['city']:
                city=new_shipping_address['city']
            telephone=''
            if new_shipping_address.has_key('telephone') and new_shipping_address['telephone']:
                telephone=new_shipping_address['telephone']             
            erp_contact_shipping = { 
                                  'parent_id'  : cust_ids[0],
                                  'type'          : 'delivery',
                                  'name'          : new_shipping_address['firstname'] + ' ' + new_shipping_address['lastname'],
                                  'street'        : new_shipping_address['street'],
                                  'zip'           : postcode,
                                  'city'          : city,
                                  'state_id'      :state_id,
                                  'fax'           :fax,
                                   'email'        : email,
                                  'country_id'    : new_shipping_address_country,
                                  'phone'         : telephone,
                                 'use_parent_address':False,
                                  }
        #End
        contact_ids = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', cust_ids[0])])
        if (contact_ids != []):
            contacts = self.pool.get('res.partner').browse(cr, uid, contact_ids)
        else:
            contacts = []
        new_contact_ids = []
        for new_contact in [erp_contact_billing , erp_contact_shipping]:   
            if (new_contact == {}):
                continue      
            skip_contact_creation = False
            i = 0
            for _contact in contacts:
                is_contact_same = True
                contact={}
                #For key in ['first_name','last_name','street','street2','zip','country_id','city','phone']:
                for key in ['name','street','zip','country_id','city','phone']:
                   
                    if (key == 'country_id'):
                        if (_contact[key]['id'] != new_contact[key]):
                            is_contact_same = False
                            break
                    else:
                        if (_contact[key] != new_contact[key]):
                            is_contact_same = False
                            break
                if (is_contact_same == True):
                    skip_contact_creation = True
                    break
                i = i + 1
            if (skip_contact_creation == False):
                id_address = self.pool.get('res.partner').create(cr, uid, new_contact)
                new_contact_ids.append(id_address)
            else:
                new_contact_ids.append(contact_ids[i])
        if not erp_contact_shipping:
            return { 'id' : cust_ids[0] , 'billing_id' : new_contact_ids[0] , 'shipping_id' :new_contact_ids[0] }
        if not erp_contact_billing:
            return { 'id' : cust_ids[0] , 'billing_id' : new_contact_ids[1] , 'shipping_id' :new_contact_ids[1] }
        
        return { 'id' : cust_ids[0] , 'billing_id' : new_contact_ids[0] , 'shipping_id' : new_contact_ids[1] }
    
    
    def import_customers(self,cr,uid):
        total_records=0#count number of imported records
        # magneto object through which connecting openerp with defined magento configuration start
        start_timestamp = str(DateTime.utc())
        magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
        last_import = magento_configuration_object[0].last_imported_customer_timestamp
        [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
        #checking server status
        if not status:
            raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password") )
#            server.endSession(session)
            return -1
        #end
        ################################################### Import Customer Groups  #########################
        #API for importing customer group from magneto 
        max_number_customer_import =30000 #max number import customer per connection
        customer_groups = server.call(session, 'customer_group.list',[])
        #creating all customer groups in openerp start
        for cus_group in customer_groups:
            cus_grp_data = {
                            'name' : cus_group['customer_group_code'],
                            'magento_id' : cus_group['customer_group_id'],
                            }
            
            cust_grp_ids = self.pool.get('res.partner.category').search(cr, uid, [('magento_id', '=', cus_grp_data['magento_id'])])
            if cust_grp_ids == []:
                cust_grp_ids = [self.pool.get('res.partner.category').create(cr, uid,cus_grp_data)]
            else:
                self.pool.get('res.partner.category').write(cr, uid,[cust_grp_ids[0]],cus_grp_data)
        #end
        #fetching all customer information from magento based on last imported time
        increment = 20000
        index = 1
        stop = index + increment - 1
        if last_import:
            customers = server.call(session, 'customer.list',[ {'updated_at': {'from': last_import},'customer_id': {'from': str(index), 'to': str(stop)}}])
        else:  
            all_customers = server.call(session, 'customer.list',[{'customer_id': {'from': str(index), 'to': str(stop)}}])
            customers = all_customers
        all_customer_id=[]
        for cus in customers:
            all_customer_id.append(cus['customer_id'])
        
        
         #Fetching Product,Based on min and max number from magneto (Due to Response error)
        min=0
        if magento_configuration_object[0].max_number_customer_import:
             max_number_customer_import=int(magento_configuration_object[0].max_number_customer_import)#In Openerp,Configured max number per connection for product 
        max=max_number_customer_import
        length_cust=len(all_customer_id)#length of all product in magneto   
        while length_cust>0:
                all_customer_id_max=all_customer_id[min:max]
                try:
                   #API to get all customer informations based on all customer    
                   info_customers = server.call(session, 'customapi_customer.itemslist',[all_customer_id_max])
                except Exception,e:
                   info_customers=[]
                    #To modify min,max and total length of product start
                min=max
                length_cust=length_cust-max_number_customer_import
                if length_cust<max_number_customer_import:
                    max=min+length_cust
                else:
                    max=max+max_number_customer_import
                #End   
              
                for info_customer in info_customers:
                    customer_address=[]
                    if info_customer.has_key('addresses') and info_customer['addresses']:
                          customer_address = info_customer['addresses']
                    #fetching customer group id from openerp
                    if info_customer.has_key('group_id') and info_customer['group_id']:
                      cust_grp_ids = self.pool.get('res.partner.category').search(cr, uid, [('magento_id', '=', info_customer['group_id'])])
                      #all categorie's object
                      category_ids =self.pool.get('res.partner.category').browse(cr,uid,cust_grp_ids)
                    #dict for customer information that we are going to insert in openerp
                    
                    erp_customer = {  
                                    'magento_id'     : info_customer['customer_id'],
                                    'export_magento' : True,
                                    'name'           : info_customer['firstname'],
                                    'email'          : info_customer['email'],
                                    'group_id'       : cust_grp_ids[0] or False,
                                    'created_at'    : info_customer['created_at'],
                                    'website_id'     : info_customer['website_id'],
                                    'customer'       : True,
                                    'modified'       : False,
                                    'supplier'       : False
                                    }
                    if info_customer['lastname']:
                         erp_customer['name'] = info_customer['firstname'] + ' ' + info_customer['lastname']
                    #searching availability of customer in openerp
                    cust_ids = self.pool.get('res.partner').search(cr, uid, [('magento_id', '=', int(erp_customer['magento_id']))])
                    if cust_ids == []:
                      if 1==1:
                        #creating customer record in openerp   
                        cust_ids = [self.pool.get('res.partner').create(cr, uid, erp_customer)]
                        if cust_ids:
                               total_records+=1 
                        for cust_grp_id in cust_grp_ids:
                               cr.execute('insert into res_partner_res_partner_category_rel (category_id,partner_id) \
                                      values (%s,%s)', (cust_grp_id, cust_ids[0]))
                        #inserting customer address in openerp
                        i =0
                        for cus_add in customer_address:
                            i +=1
                            try:
                                country_id = self.pool.get('res.country').name_search(cr, uid, cus_add['country_id'])[0][0]
                            except:
                                if 'country_id' in cus_add.keys():
                                        new_country = { 
                                                        'name': cus_add['country_id'],
                                                        'code': cus_add['country_id']
                                                       }
                                        country_id = self.pool.get('res.country').create(cr, uid, new_country)
                            phone=''
                            if info_customer.has_key('phone') and info_customer['phone']:
                                phone=info_customer['phone']
                            fax=''
                            if cus_add.has_key('fax') and cus_add['fax']:
                                fax=cus_add['fax']
                            postcode=''
                            if cus_add.has_key('postcode') and cus_add['postcode']:
                                postcode=cus_add['postcode']
                            city=''
                            if cus_add.has_key('city') and cus_add['city']:
                                city=cus_add['city']     
                            telephone=''
                            if cus_add.has_key('telephone') and cus_add['telephone']:
                                telephone=cus_add['telephone']          
                            street=''
                            if cus_add.has_key('street') and cus_add['street']:
                                street=cus_add['street']
                                
                            cus_address={
                                          'magento_address_id': cus_add['customer_address_id'],
                                          'type'  : 'delivery',
                                          'street': street,
                                          'zip'  : postcode,
                                          'fax' : fax ,
                                          'city' : city,
                                          'country_id': country_id,
                                          'email': info_customer['email'],
                                          'mobile': phone,
                                          'phone': telephone,
                                          'use_parent_address':False,
                                          #'is_default_shipping' : cus_add['is_default_shipping'],
                                         # 'is_default_billing'  : cus_add['is_default_billing'],
                                         }
                            
                            if cus_add.has_key('region_id') and   cus_add['region_id'] and int(cus_add['region_id']) > 0:
                                state_id = self.pool.get('res.country.state').search(cr, uid, [('magento_id', '=', cus_add['region_id'])])
                                if state_id:
                                      self.pool.get('res.country.state').write(cr, uid, [state_id[0]], {'name' : cus_add['region'] } )
                                      cus_address['state_id'] = state_id[0]
        #                        else:
        #                             state_id = [self.pool.get('res.country.state').create(cr, uid, {'name' : cus_add['region'] ,'magento_id':cus_add['region_id'],'country_id' : country_id} )]
        #                        cus_address['state_id'] = state_id[0]
                            elif cus_add.has_key('region') and cus_add['region']:
                                      state_id = self.pool.get('res.country.state').search(cr, uid, [('name', '=', cus_add['region']),('country_id','=',country_id)])
                                      if state_id:
                                          self.pool.get('res.country.state').write(cr, uid, [state_id[0]], {'name' : cus_add['region'] } )
                                          cus_address['state_id'] = state_id[0]
        #                              else:
        #                                 state_id = [self.pool.get('res.country.state').create(cr, uid, {'name' : cus_add['region'],'country_id' : country_id } )]
                                      
                            if 'is_default_shipping' in cus_add.keys() and cus_add['is_default_shipping']:
                               cus_address['type'] = 'delivery'
                            if cus_add['is_default_billing']: 
                               cus_address['type'] = 'invoice'
                            if cus_add['is_default_billing'] and cus_add['is_default_shipping']:
                               cus_address['type'] = 'default'    
                            if not cus_add['is_default_billing'] and not cus_add['is_default_shipping']:
                               cus_address['type'] = 'delivery'
                            
                            if i==1:
                               
                               cus_address['is_company']  = True  
                               cust_add_ids = [self.pool.get('res.partner').write(cr, uid,[cust_ids[0]], cus_address)]
                               
                            else:
                                 
                                 cus_address['parent_id'] = cust_ids[0]    
                                 cus_address['name'] = cus_add['firstname'] + ' ' + cus_add['lastname']
                                 cust_add_ids = [self.pool.get('res.partner').create(cr, uid, cus_address)]
        #              except:
        #                  pass
                    else:
                        total_records+=1
                        self.pool.get('res.partner').write(cr, uid, [cust_ids[0]], erp_customer)
                        partner_address=[]
                        #Group Updation in openerp
                        for cust_grp_id in cust_grp_ids:
                                cr.execute("""select category_id from res_partner_res_partner_category_rel where
                                    category_id = %s and  partner_id = %s """ , (cust_grp_id, cust_ids[0])  )
                                if not cr.dictfetchall():
                                    cr.execute('insert into res_partner_res_partner_category_rel (category_id,partner_id) \
                                    values (%s,%s)', (cust_grp_id, cust_ids[0]))
                        #Address updation for a specified customer in openerp
                        
                        for cus_add in customer_address:
                            
                            #searching country availability in openerp start
                            try:
                                country_id = self.pool.get('res.country').name_search(cr, uid, cus_add['country_id'])[0][0]
                            except:
                                new_country = { 
                                                'name': cus_add['country_id'],
                                                'code': cus_add['country_id']
                                               }
                                country_id = self.pool.get('res.country').create(cr, uid, new_country)
                            #end
                            phone=''
                            if info_customer.has_key('phone') and info_customer['phone']:
                                phone=info_customer['phone']
                                
                            fax=''
                            if cus_add.has_key('fax') and cus_add['fax']:
                                fax=cus_add['fax']
                            postcode=''
                            if cus_add.has_key('postcode') and cus_add['postcode']:
                                postcode=cus_add['postcode']
                            city=''
                            if cus_add.has_key('city') and cus_add['city']:
                                city=cus_add['city']     
                            telephone=''
                            if cus_add.has_key('telephone') and cus_add['telephone']:
                                telephone=cus_add['telephone']              
                            street=''
                            if cus_add.has_key('street') and cus_add['street']:
                                street=cus_add['street']    
                            company=''    
                            if cus_add.has_key('company') and cus_add['company']:
                                company=cus_add['company']        
                            cus_address = { 
                                    'magento_address_id'   : cus_add['customer_address_id'],
                                     'partner_id'  : cust_ids[0],
                                     'type'        : 'delivery',
                                     
                                      'street'     : street,
                                      'zip'        : postcode,
                                      'city'       : city,
                                      'email'      : info_customer['email'],
                                       'mobile'    : phone,
                                      'country_id' : country_id,
                                      'fax'        : fax ,
                                      'phone'      : telephone,
                                      'company':company,
                                      'is_default_shipping' : cus_add['is_default_shipping'],
                                      'is_default_billing' : cus_add['is_default_billing'],
                                         'use_parent_address':False,
                                           }
                            #searching state availability in openerp start
                            if cus_add.has_key('region_id') and   cus_add['region_id'] and int(cus_add['region_id']) > 0:
                                state_id = self.pool.get('res.country.state').search(cr, uid, [('magento_id', '=', cus_add['region_id'])])
                                if state_id:
                                      self.pool.get('res.country.state').write(cr, uid, [state_id[0]], {'name' : cus_add['region'] } )
                                      cus_address['state_id'] = state_id[0]
        #                        else:
        #                             state_id = [self.pool.get('res.country.state').create(cr, uid, {'name' : cus_add['region'] ,'magento_id':cus_add['region_id'],'country_id' : country_id} )]
        #                        cus_address['state_id'] = state_id[0]   
                            elif cus_add.has_key('region') and cus_add['region']:
                                      state_id = self.pool.get('res.country.state').search(cr, uid, [('name', '=', cus_add['region']),('country_id','=',country_id)])
                                      if state_id:
                                         self.pool.get('res.country.state').write(cr, uid, [state_id[0]], {'name' : cus_add['region'] } )
                                         cus_address['state_id'] = state_id[0]
        #                              else:
        #                                  state_id = [self.pool.get('res.country.state').create(cr, uid, {'name' : cus_add['region'],'country_id' : country_id } )]
        #                              cus_address['state_id'] = state_id[0]         
                            #end
                            if cus_add['is_default_shipping']:
                               cus_address['type'] = 'delivery'
                            if cus_add['is_default_billing']: 
                               cus_address['type'] = 'invoice'
                            if cus_add['is_default_billing'] and cus_add['is_default_shipping']:
                               cus_address['type'] = 'default'     
                            if not cus_add['is_default_billing'] and not cus_add['is_default_shipping']:
                               cus_address['type'] = 'default' 
                            #checking availability of address in openerp for a specified customer
                            cust_add_ids = self.pool.get('res.partner').search(cr, uid, [('magento_address_id', '=', cus_address['magento_address_id'])])
                            if  cust_add_ids:
                                self.pool.get('res.partner').write(cr, uid, [cust_add_ids[0]], cus_address )
                                partner_address.append(cust_add_ids[0])
                            else:
                                cus_address['parent_id'] = cust_ids[0]    
                                cus_address['name'] = cus_add['firstname'] + ' ' + cus_add['lastname']           
                                cust_add_ids = [self.pool.get('res.partner').create(cr, uid, cus_address)]
                                partner_address.append(cust_add_ids[0])
                        #unlink the old address for a specified customer in openerp start
                        address_ids = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', cust_ids[0])]) 
#                        for line in address_ids:
#                            if line not in partner_address: 
#                                self.pool.get('res.partner').write(cr, uid, [line], {'parent_id':False,'magento_id':-2} )        
                cr.commit()
        #updating last import time in openerp database
        if magento_configuration_object[0].id:
            self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'last_imported_customer_timestamp':start_timestamp})   
        ##server.endSession(session)
        return total_records
    
magento_configuration()    

# Partner  Object Configuration  based on magento
class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'magento_id':fields.integer('Magento ID'),
        'magento_address_id':fields.integer('Magento Address ID'), # Store magento Address also in res.partner
        'email':fields.char('Email', size=128),
        'export_magento' : fields.boolean('Export To Magento'),
        'group_id' : fields.many2one('res.partner.category','Customer Type'),
        'created_at': fields.date('Created at'), 
        'modified':fields.boolean('Modified since last synchronization'),
        'website_id' : fields.selection([('0','Admin'),('1','Main website'),('2','dantunes.eu')],'Associate to Website'),
       'company':fields.char('Company',size=256),
    }
    #creating index for searching records  
    def _auto_init(self, cr, context=None):
        super(res_partner, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'partner_magneto_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX partner_magneto_id ON res_partner (magento_id)')
            
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'partner_export_magneto_modified_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX partner_export_magneto_modified_id ON res_partner (export_magento,modified)') 
     
    #After any modification in record, modified field should be true for specific record. 
    def write(self, cr, uid, ids, vals, context={}):
        if not vals.has_key('modified'):
            vals['modified'] = True
        return super(res_partner, self).write(cr, uid, ids, vals, context)
      
    _defaults = {
        'magento_id': lambda *a: -1,
        'modified': lambda *a: True,
    }
   
res_partner()

# Inherit res_partner_category for adding magento ID in Openerp
class res_partner_category(osv.osv):
    _inherit = 'res.partner.category'
    _columns = {
        'magento_id':fields.char('Magento ID', size=128),
    }
    _defaults = {
        'magento_id': lambda *a: -1,
    }
   
res_partner_category()

# Inherit res_partner_state for adding magento ID in Openerp
class res_country_state(osv.osv):
    _inherit = 'res.country.state'
    _columns = {
        'magento_id':fields.char('Magento ID', size=128),
    }
    _defaults = {
        'magento_id': lambda *a: -1,
    }
   
res_country_state()