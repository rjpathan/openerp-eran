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
import mimetypes
from pprint import pprint
import base64, urllib
from openerp.tools.translate import _
t_cat=0
#inherit magento_configuration class to add product import and export functions
class magento_configuration(osv.osv):
    _inherit = 'magento.configuration'
    
    #getting all parrent category from openerp for a specific category
    def _category_parent(self, cr, uid,category_obj):
        total_obj =[]
        magneto=category_obj.magento_id
        if(int(magneto) != -1):
            total_obj = total_obj + [category_obj]
            new_category_obj =[category_obj.parent_id]
        else:
            new_category_obj = []
            return []
        for i in new_category_obj:
             if i:
                 total_obj = total_obj + self.pool.get('magento.configuration')._category_parent(cr,uid,i)
        return total_obj  
    
    def export_products(self, cr, uid):
        total_no_of_records=0
        magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
        if magento_configuration_object==None:
              raise osv.except_osv(_('Import/Export is in progress!'),_("Import/Export Products is All ready Running ") )
        try :
            # magneto object through which connecting openerp with defined magneto configuration start
            magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
#            if not status:
#                set_export_finished()  
#                return -1
            #end
            #searching exporting product ids from openerp 
            prod_ids = self.pool.get('product.product').search(cr, uid, [('export_to_magento', '=', 'True'),('modified', '=', 'True')])
            #making all searched product's object
            products=self.pool.get('product.product').browse(cr, uid, prod_ids)
            attribute_sets = server.call(session, 'product_attribute_set.list');
#            [{'name': 'Ajna', 'set_id': '16'}, {'name': 'Asana Mat', 'set_id': '17'}, {'name': 'Bohemia', 'set_id': '18'}, {'name': 'Default', 'set_id': '4'}, {'name': 'Test Default', 'set_id': '21'}, {'name': 'Tranquillo', 'set_id': '19'}, {'name': 'Zergatik', 'set_id': '20'}]
            #searching availability of product in magneto start
            default_a_s = attribute_sets[0]['set_id']
            for set in attribute_sets:
                 if set['name']=='Default':
                        default_a_s = set['set_id']
            all_product_id=[]
            for prod in products:
                if prod.magento_id != -1:
                    all_product_id.append(str(prod.magento_id))
            try:
               #API to get all products information from magneto       
               all_info_products  = server.call(session, 'customapi_product.itemslist',[all_product_id])
            except:
               all_info_products=[]   
            #end
            local_cr = pooler.get_db(cr.dbname).cursor()
            for prod in products:
                try:
                    if prod.code:
                        product_data = {
                            'status': True,
                            'name': prod.name,  
                            'openerp_name':prod.name,
                            'sku': prod.code,
                            'msrp':str(prod.list_price),
                        }
                        if prod.magento_attr_id:
                              attribute_set_id = str(prod.magento_attr_id)
                        else : 
                                attribute_set_id = default_a_s
                        if prod.magento_name:
                             product_data['name']=prod.magento_name
                        if prod.list_price:
                            product_data['price'] = str(prod.list_price) 
                        if prod.weight:    
                            product_data['weight'] = str(prod.weight)
                        if prod.taxes_id and  prod.taxes_id[0].magento_id:
                                       product_data['tax_class_id']=str(prod.taxes_id[0].magento_id)
                                       product_data['price']=prod.list_price
                        #checking availability of customer in magneto
                        available=False
                        if prod.magento_id!=-1:
                           info_product=[product for product in all_info_products if int(prod.magento_id)==int(product['0']['entity_id'])]
                           if info_product:
                              available=True
                        #creating new product in magneto 
                        if (prod.magento_id == -1) or (not available):
                            #API to create product in magneto
                            if prod.product_lines :
                                    #API to create product in magneto based on product typeattribute_set_id
#                                    magento_id = server.call(session, 'catalog_product.create', ['bundle', attribute_sets[0]['set_id'], prod.code, product_data]);
                                    magento_id = server.call(session, 'catalog_product.create', ['bundle', attribute_set_id, prod.code, product_data]);
                            else : 
                                    magento_id = server.call(session, 'catalog_product.create', ['simple', attribute_set_id, prod.code, product_data]);
                            if magento_id:
                                total_no_of_records+=1 
                            ###############################export information end################################################################
                            self.pool.get('product.product').write(local_cr, uid, prod.id, {'magento_id': magento_id, 'modified': False})
                        else:
                            #updating product information in magneto
                            if available :
                               #API to update product in magneto 
                               server.call(session, 'catalog_product.update', [prod.magento_id,product_data]);
                               total_no_of_records+=1 #count number of exported category
                               self.pool.get('product.product').write(local_cr, uid, prod.id, {'modified': False})
                    else:
                        pass
                except Exception,e:
                    pass  
            local_cr.commit()
            all_product_id=[]
            products=self.pool.get('product.product').browse(local_cr, uid, prod_ids)
            for prod in products:
                if prod.magento_id != -1:
                    all_product_id.append(str(prod.magento_id))
            try:        
                #API to get all products information from magneto 
                all_info_products  = server.call(session, 'customapi_product.itemslist',[all_product_id])
            except:
                all_info_products=[]  
             ####################### Exporting Images####################3
            for prod in products:
                try:
                            if prod.magento_id!=-1:
                              info_product = server.call(session, 'product.info',[str(prod.magento_id)])
                              if int(info_product['product_id'])==int(prod.magento_id):
                                available=True
                                   
                except:
                            available=False
                #searching availability of image based on product from openerp
                images_id = self.pool.get('product.images').search(local_cr,uid,[('product_id','=',prod.id),('modified','=',True)]) 
                #making image objects based on all images_id
                images = self.pool.get('product.images').browse(local_cr, uid, images_id) 
                #updating images in magneto start
                img_list=[]
                try:
                        if prod.magento_id!=-1:
                            img_list = server.call(session, 'catalog_product_attribute_media.list',[ prod.magento_id ])
        #               
                        if not len(img_list)==len(images_id):
                           if prod.magento_id >=1 and available and len(images):
                                            
                                            for image in images: 
                                                types = []
                                                if image.small_image:
                                                    types.append('small_image')
                                                if image.base_image:
                                                    types.append('image')
                                                if image.thumbnail:
                                                    types.append('thumbnail')
                                                if image.filename and image.modified and not image.image:
                                                        image1={}
                                                      
                                                        image_update = {
                                                                            'name' : image.name,
                                                                            #'image' : image.image,
                                                                              'label' : image.name,
                                                                              'exclude' : image.exclude,
                                                                              'types': types,
                                                                              'file':{
                                                                        'name':image.name,
                                                                        'content': image.preview,
                                                                        'mime':  'image/jpeg',
                                                                        }
                                                                             }
                                                        server.call(session, 'catalog_product_attribute_media.create', [prod.magento_id,image_update]);
                                                else:
                                                    try:            
                                                          if image.image:
                                                            image_data = {
                                                                  'name' : image.name,
                                                                  'label' : image.name,
                                                                  'exclude' : image.exclude,
                                                                  'types': types,
                                                                  'file':{
                                                                        'name':image.name,
                                                                        'content': image.image,
                                                                        'mime': image.link and image.url and mimetypes.guess_type(image.url)[0]  or 'image/jpeg',
                                                                        }
                                                                  }     
                                                            result = server.call(session, 'catalog_product_attribute_media.create', [prod.magento_id, image_data]);
                                                    except:
                                                        pass        
                                                for image1 in img_list:
                                                      if  image1['label'] == image.name:
                                                           self.pool.get('product.images').write(local_cr, uid, image.id, { 'modified': False,'filename' : image1['url'],'link' : True, 'position' : image1['position']})
                except:
                    pass
            ####################################Images Export end######################################    
            for prod in products:
                if prod.magento_id != -1:
                  #TO get all parent category from openerp for each product's category  
                  category_total_obj=self.pool.get('magento.configuration')._category_parent(local_cr, uid, prod.categ_id)
                  magento_cat_ids = []
                  for product in all_info_products:
                      if int(prod.magento_id)==int(product['0']['entity_id']):
                        if  product.has_key('category_ids'):
                            magento_cat_ids = product['category_ids']
                        elif  product.has_key('categories'):
                           magento_cat_ids = info_category['categories']
		  try:
                     #Remove product form category in magneto
                     for assigned_category_id in magento_cat_ids:
                        server.call(session, 'category.removeProduct', [assigned_category_id, prod.magento_id]);
                     #assigning a specific product in all category in magneto
                     for category_each_obj in category_total_obj:
                        server.call(session, 'category.assignProduct', [category_each_obj.magento_id, prod.magento_id]);
		  except Exception,e:
			if str(e).find('Fault 102')>-1:
				pass
			else:
				return -1
            local_cr.commit()
            local_cr.close() 
#            set_export_finished()
            return total_no_of_records
        except Exception,e:
            return -1
    
    
    def export_categories(self, cr, uid):
        total_no_of_records=0
       
            #magneto object through which connecting openerp with defined magneto start
        magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
        [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
        if not status:
                raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                  please check the url,username and password "))
                return -1
        try:
            #To search category from openerp which have to export in magneto
            cat_ids = self.pool.get('product.category').search(cr, uid, [('update_to_magneto', '=', 'True'),('modified', '=', 'True')])
            category_list = cat_ids #all category which going to export in magneto
            local_cr = pooler.get_db(cr.dbname).cursor()  #local cursor ,magneto_id will be update in openerp using this cursor.  
            for category in category_list:
                cat = self.pool.get('product.category').browse(local_cr, uid, category)
                try:
                    category_data = {
                            'name': cat.name,  
                            'available_sort_by': 'name,price',
                            'is_active': 1,
                            'default_sort_by': 'price',
                            'use_parent_review_settings':1, 
                            'include_in_menu': False,}
                    #Searching availability of category in magneto start
                    available=False
                    try:
                        if cat.magento_id != -1:
                            info_category = server.call(session, 'category.tree',[str(cat.magento_id)])
                            if int(info_category['category_id'])==int(cat.magento_id):
                               available=True
                    except:
                        info_category = {
                                'category_id' : '0'
                            }
                    #end
                    if (cat.magento_id == -1) or (not available):
                        #API To create category in magneto
                        magento_id = server.call(session, 'category.create', [1, category_data])
                        if magento_id:
                           total_no_of_records+=1 
                        #updating magneto_id in openerp .
                        self.pool.get('product.category').write(local_cr, uid, cat.id, {'magento_id': magento_id, 'modified': False})
                    else:
                        if available:
                            #updating category information in magneto 
                            server.call(session, 'category.update', [cat.magento_id, category_data])
                            total_no_of_records+=1
                            self.pool.get('product.category').write(local_cr, uid, cat.id, {'modified': False})
                except:
                   pass
            local_cr.commit()#all information of category will update in openerp
            #making relationship between child and parents category in magneto.
            for category in category_list:
                cat = self.pool.get('product.category').browse(local_cr, uid, category)
                if cat.parent_id.magento_id and (cat.parent_id.magento_id != -1) and cat.magento_id != -1:
                        server.call(session, 'category.move', [cat.magento_id, cat.parent_id.magento_id])
                elif magento_configuration_object[0].magento_root_cat_id != -1 and cat.magento_id != -1:
                        server.call(session, 'category.move', [cat.magento_id, magento_configuration_object[0].magento_root_cat_id])
            local_cr.commit()
            local_cr.close()
            return total_no_of_records
        except: 
            return -1 
    
    def _create_category(self, cr, uid, info_category, magento_configuration_object):
        
        global t_cat #global variable that count total no of records created in openerp
        category = { 'magento_id' : info_category['category_id'],
          'name' : info_category['name'],
          'modified' : False,
          'update_to_magneto':True,
        }
        #using defined level in magneto ,fetching all parents category .
        if (info_category['level'] != '0'):
            if info_category['parent_id'] == str(magento_configuration_object[0].magento_root_cat_id):
                category['parent_id'] = False
            else:
                cat_ids = self.pool.get('product.category').search(cr, uid, [('magento_id', '=', info_category['parent_id'])])
                if cat_ids == []:
                    pass
                else:
                    category['parent_id'] = cat_ids[0]
        else:
            self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'magento_root_cat_id':category['magento_id']})
        # to search category availability in openerp database
        cat_ids = self.pool.get('product.category').search(cr, uid, [('magento_id', '=', category['magento_id'])])
        #Checking for parent category in dantunes
        if ('parent_id' in category.keys() and not category['parent_id']) or ('parent_id' not in category.keys()):
             categ_id = self.pool.get('product.category').search(cr, uid, [('name', '=', 'Webshop')])
             if len(categ_id)!=0:
                   category['parent_id']=categ_id[0]
             else:
                    category['parent_id'] = self.pool.get('product.category').create(cr, uid,{'name': 'Webshop'})    
        if cat_ids == []:
            #creating category in openerp database
            cat_ids = [self.pool.get('product.category').create(cr, uid, category)]
            if cat_ids:
                t_cat+=1
        else:
            #updating all category information from magneto to openerp in exist category_id
            self.pool.get('product.category').write(cr, uid, [cat_ids[0]], category)
        if cat_ids == []:
            return -1  
        for child in info_category['children']:
           self.pool.get('magento.configuration')._create_category(cr, uid, child, magento_configuration_object) 
        return t_cat  

    def import_categories(self, cr, uid):
            
                # magneto object through which connecting openerp with defined magneto configuration start
            start_timestamp = str(DateTime.utc())
            magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
            if magento_configuration_object==None:
                raise osv.except_osv(_('Import/Export is in progress!'),_("Import/Export Products is All ready Running ") )
                
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
            if not status:
                    raise osv.except_osv(_('There is no connection!'),_("There is no connection established with magento server\n\
                    please check the url,username and password") )
                    return -1 
                #end
            try:     
                #fetching all category information from magneto using the following API.
                info_category = server.call(session, 'category.tree',[])
                #Creating all records in openerp using _create_category function.
                total_no_of_records=self.pool.get('magento.configuration')._create_category(cr, uid, info_category, magento_configuration_object)
                if magento_configuration_object[0].id:
                  self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'last_imported_category_timestamp':start_timestamp})
            except Exception,e:
#                server.endSession(session)
                return -1 
#            server.endSession(session)
            return total_no_of_records
        
    #through this function we can create product while importing product
    #while import sale order ,also use this method for product creation
    def  product_creation(self,cr,uid,info_product):
          try:
                info_category=info_product
                info_product=info_product['0']
                product = { 'magento_id' : info_product['entity_id'],
                  'name' : info_product['name'],
                  'default_code' : info_product['sku'],
                  'modified' : False,
                  'type':'product',
                  'export_to_magento': True,
                }
                try:
                    product['list_price'] = info_product['price']
                except:
                    product['list_price'] = '0.00'
                try:
                    product['weight'] = info_product['weight']
                except:
                    product['weight'] = '0.00'
                
                if info_category.has_key('category_ids'):
                    magento_cat_ids = info_category['category_ids']
                elif info_category.has_key('categories'):
                    magento_cat_ids = info_category['categories']
                else:
                    magento_cat_ids = []  
                #searching category availability in openerp
                if magento_cat_ids:
                    cat_ids = self.pool.get('product.category').search(cr, uid, [('magento_id', '=', magento_cat_ids[0])])
                    if (cat_ids[0]):
                        product['categ_id'] = cat_ids[0]
                    else:
                        product['categ_id'] = magento_params[0].default_category.id    
                else:
                    product['categ_id'] = magento_params[0].default_category.id    
                #searching product availability in openerp
                prod_ids = self.pool.get('product.product').search(cr, uid, [('magento_id', '=', product['magento_id'])])
                #####image fetching for specific product###############################
                try:
                   img_list = server.call(session, 'catalog_product_attribute_media.list',[product['magento_id']])
                except:
                   img_list=[]
                   
                prod_ids = [self.pool.get('product.product').create(cr, uid, product)]
                if prod_ids:
                   total_no_of_records+=1 #count number of imported records in openerp
                #####Import image in openerp start#####################################   
                for image in img_list:    
                    images_dict = {
                                   'name' : image['label'],
                                   'filename' : image['url'],
                                   'position' : image['position'],
                                   'exclude' : image['exclude'],
                                   'product_id' : prod_ids[0],
                                  # 'file' : image['file']
                                }
                    for type in image['types']:
                        images_dict[type] = True
                        if type == 'thumbnail':
                                (filename, header) = urllib.urlretrieve(image['url'])
                                f = open(filename , 'rb')
                                img = base64.encodestring(f.read())
                                f.close()
                                self.pool.get('product.product').write(cr,uid,prod_ids[0],{'product_image' :img})
                        self.pool.get('product.images').create(cr, uid, images_dict)     
          except:
                pass 
            
          return prod_ids  
            
    def import_products(self, cr, uid,context=None):
        if context==None:
            context={}
        total_no_of_records=0
        start_timestamp = str(DateTime.utc())
        magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
        if magento_configuration_object==None:
              raise osv.except_osv(_('Import is in progress!'),_("Import Products is All ready Running ") )
        try:
            # magneto object through which connecting openerp with defined magneto configuration start
            magento_configuration_object = self.pool.get('magento.configuration').get_magento_configuration_object(cr, uid)
            last_import = magento_configuration_object[0].last_imported_product_timestamp # last imported time
            if magento_configuration_object[0].sync_status=='Running':
                 raise osv.except_osv(_('Import is in process!'),_("Import Products is All ready Running ") )
            [status, server, session] = self.pool.get('magento.configuration').magento_openerp_syn(cr, uid)
            if not status:
                server.endSession(session)
                return -1
            #end 
        except:
#            server.endSession(session)
            return -1
        self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'sync_status':'Running'})
        increment = 30000
        index = 1
        max_number_product_import =30000 #max number import product per connection
        attribute_sets = server.call(session, 'product_attribute_set.list');
        while True:
              stop = index + increment - 1
              #fetching all information from magneto based on last imported time
              if last_import:
                  all_products = server.call(session, 'product.list',[{'updated_at': {'from': last_import}, 'product_id': {'from': str(index), 'to': str(stop)}}])
                  products = all_products
              else: 
                  all_products = server.call(session, 'product.list',[{'product_id': {'from': str(index), 'to': str(stop)}}]) 
                  products = all_products
              index = stop + 1
              all_product_id=[]
              for prod in products:
                    all_product_id.append(prod['product_id'])
              #Fetching Product,Based on min and max number from magneto (Due to Response error)
              min=0
              if magento_configuration_object[0].max_number_product_import:
                 max_number_product_import=int(magento_configuration_object[0].max_number_product_import)#In Openerp,Configured max number per connection for product 
              max=max_number_product_import
              length_prod=len(all_product_id)#length of all product in magneto   
              
              while length_prod>0:
                all_product_id_max=all_product_id[min:max]
            
                #API to get all products information from magneto 
                try:
                    info_products = server.call(session, 'customapi_product.itemslist',[all_product_id_max])
                except:
                    info_products=[]  
                #To modify min,max and total length of product start
                min=max
                length_prod=length_prod-max_number_product_import
                if length_prod<max_number_product_import:
                    max=min+length_prod
                else:
                    max=max+max_number_product_import
                #End
                for info_product in info_products:
                    try:
                        info_category=info_product
                        info_product=info_product['0']
                        tax_parcent=False
                        try:
                                tax_parcent = info_category['tax_percent']
                                tax_class_id = info_product['tax_class_id']
                                if tax_parcent:
                                        tax_id = self.pool.get('magento.configuration').get_tax_id(cr, uid, tax_parcent)
                                        if tax_class_id:
                                                 self.pool.get('account.tax').write(cr,uid,tax_id,{'magento_id':int(tax_class_id)})
                                        if (tax_id == 0):
                                                      raise  
                                        else:
                                                 tax_ids = [[6,0,[tax_id]]]   
                        except Exception,e:
                                    tax_ids = []   
                        product = { 'magento_id' : info_product['entity_id'],
                          'magento_name' : info_product['name'],
                          'name':info_product['name'],
                          'default_code' : info_product['sku'],
                          'modified' : False,
                          'type':'product',
                          'export_to_magento': True,
                           'taxes_id':tax_ids,
                           'magento_attr_id':info_product['attribute_set_id']
#                          'description':info_product['description'],
                        }
                        if 'openerp_name' in info_product.keys() and info_product['openerp_name']:
                            product['name']=info_product['openerp_name']
                        product['list_price'] = info_product['price']    
                        try:
                            product['weight'] = info_product['weight']
                        except:
                            product['weight'] = '0.00'
                        if info_product.has_key('type_id') and info_product['type_id'] =='bundle':
                           product['magento_pro_type'] = info_product['type_id']
                        if info_category.has_key('category_ids') and info_category['category_ids'] :
                            magento_cat_ids = info_category['category_ids']
                        elif info_category.has_key('categories') and info_category['categories']:
                            magento_cat_ids = info_category['categories']
                        else:
                            magento_cat_ids = []  
                        #searching category availability in openerp
                        if magento_cat_ids:
                            cat_ids = self.pool.get('product.category').search(cr, uid, [('magento_id', '=', magento_cat_ids[-1])])
                            if (cat_ids[0]):
                                product['categ_id'] = cat_ids[0]
                            else:
                                product['categ_id'] = magento_configuration_object[0].default_category.id    
                        else:
                            product['categ_id'] = magento_configuration_object[0].default_category.id    
                        #searching product availability in openerp
                        prod_ids = self.pool.get('product.product').search(cr, uid, [('magento_id', '=', product['magento_id'])])
                        #####image fetching for specific product###############################
                       # try:
                        img_list = server.call(session, 'catalog_product_attribute_media.list',[product['magento_id']])
                        
#                        except:
#                           img_list=[]  
                        ########End###########################################################
                        if prod_ids == []:
                            #inserting new product in openerp
                            product['magento_name']=product['name']
                            prod_ids = [self.pool.get('product.product').create(cr, uid, product)]
                            if prod_ids:
                               total_no_of_records+=1 #count number of imported records in openerp
                            #####Import image in openerp start#####################################
                            id1 = []   
                            for image in img_list:    
                                images_dict = {
                                               'name' : image['label'],
                                               'filename' : image['url'],
                                               'position' : image['position'],
                                               'exclude' : image['exclude'],
                                               'product_id' : prod_ids[0],
                                              # 'file' : image['file']
                                            }
                               
                                for type in image['types']:
                                    
                                    images_dict[type] = True
                                    if type == 'thumbnail':
                                            (filename, header) = urllib.urlretrieve(image['url'])
                                            f = open(filename , 'rb')
                                            img = base64.encodestring(f.read())
                                            f.close()
#                                            self.pool.get('product.product').write(cr,uid,prod_ids[0],{'image_medium' :img})
                                self.pool.get('product.images').create(cr, uid, images_dict)
                            
                            #self.pool.get('product.product').write(cr,uid,prod_ids[0],{'image_ids' :id1})
                            #End#######################################################################                      
                        else:
                            total_no_of_records+=1 
                            #updating product information in openerp
                            #Dantunes Requirement to dont update category#
                            if 'categ_id' in product.keys():
                                   del(product['categ_id'])
                            ##########End##########
                            if 'update' not in context.keys():
                                  self.pool.get('product.product').write(cr, uid, [prod_ids[0]], product)
                           
                            #####Import image in openerp start#######################################
                            for image in img_list:
                                images_dict = {
                                               'name' : image['label'] or 'test',
                                               'filename' : image['url'],
                                               'position' : image['position'],
                                               'exclude' : image['exclude'],
                                               'product_id' : prod_ids[0],
                                            }
                                for type in image['types']:
                                    images_dict[type] = True
                                    if type == 'thumbnail':
                                            (filename, header) = urllib.urlretrieve(image['url'])
                                            f = open(filename , 'rb')
                                            img = base64.encodestring(f.read())
                                            f.close()
#                                            self.pool.get('product.product').write(cr,uid,prod_ids[0],{'image_medium' :img})
                                #searching product image in openerp
                                prod_img_id = self.pool.get('product.images').search(cr, uid, [('product_id', '=', prod_ids[0]),('filename' ,'=',image['url'])])
                                if prod_img_id :
                                    #updating product image in openerp if image exist
                                    self.pool.get('product.images').write(cr, uid, [prod_img_id[0]],images_dict)
                                else: 
                                    #creating product image in openerp   
                                    self.pool.get('product.images').create(cr, uid, images_dict) 
                            #End####################################################################### 
                        if prod_ids == []:
                            return -1
                    except:
                        pass
                    
              cr.commit()
              #Start,Sub product configuration in product master for bundle product 
              
              bundle_product_ids = self.pool.get('product.product').search(cr, uid, [('magento_pro_type', '=','bundle')])
              bundle_product_objects= self.pool.get('product.product').browse(cr,uid,bundle_product_ids)
              
              for bundle_product_object in bundle_product_objects:
                    try:
                       #API to fetch the bundle product from magneto 
                       sub_products_info = server.call(session, 'customapi_product.ktreebundle',[str(bundle_product_object.magento_id)]) 
                    except:
                       sub_products_info=[] 
                    for sub_product_line in  sub_products_info:
                        
                        #searching subproduct from openerp
                        sub_prod_ids = self.pool.get('product.product').search(cr, uid, [('magento_id', '=', sub_product_line['product_id'])])
                        if sub_prod_ids:
                            sub_prod_obj=self.pool.get('product.product').browse(cr,uid,sub_prod_ids[0])
                            #sub product information
                            sub_product_info = {
                                        'bundle_product_id' :  bundle_product_object.id,
                                        'product_id'        :  sub_prod_obj.id,
                                        'product_uom'       :   sub_prod_obj.uom_id.id,
                                        'package_qty'       :  sub_product_line['selection_qty'],
                                        'sale_price'        :  sub_product_line['selection_price_value'],
                                        }
                            package_material=self.pool.get('product.lines').search(cr, uid,
                                                                                   [('bundle_product_id','=',bundle_product_object.id),
                                                                                    ('product_id','=',sub_prod_obj.id)]) 
                            #updating subproduct in openerp for specific bundle product
                            if  package_material:
                                self.pool.get('product.lines').write(cr,uid,package_material[0],sub_product_info)
                            else:
                                self.pool.get('product.lines').create(cr,uid,sub_product_info)  
                    cr.commit()       
              #updating last imported time in openerp database
              if (all_products == []):
                    if magento_configuration_object[0].id:
                       self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'last_imported_product_timestamp':start_timestamp})
                       self.pool.get('magento.configuration').write(cr, uid, [magento_configuration_object[0].id], {'sync_status':'Idle'})  
                    
                    server.endSession(session)
                    return total_no_of_records
        server.endSession(session)
        return -1        
magento_configuration()    


###############################################################Product Lines For Bundle Product ########################################
class product_lines(osv.osv):
   _name='product.lines'
   _rec_name = 'product_id'
    
   _columns = {
               
       'bundle_product_id'    :  fields.many2one('product.product', 'Product'),
       'package_qty'          :  fields.float('Product Qty',),
       'product_uom'          :  fields.many2one('product.uom', 'Product UOM',), 
       'product_id'           :  fields.many2one('product.product', 'Product'), 
       'product_code'         :  fields.char('Product Code',size=256),
       'sale_price'           :  fields.float('Sale Price'), 
                  
              }    
   _defaults = {
                 'package_qty' : lambda *a: 1.0,
               }
    
product_lines() 

##################################################################################################################################################

# Products Object Configuration 
class product_product(osv.osv):
    _name = 'product.product'
    _inherit ='product.product'
   
    #updating virtual qty for each product
    def _product_qty_magento(self, cr, uid, ids, name, arg, context={}):
        qtys = super(product_product, self).read(cr,uid,ids,['qty_available','virtual_available','incoming_qty','outgoing_qty'],context)
        magento = {}
        for element in qtys:
            magento[element['id']]=element['virtual_available']-element['incoming_qty']
        return magento
  
    _columns = {
        'modified'          : fields.boolean('Modified since last synchronization'),
        'magento_id'        : fields.integer('Magento ID'),
        'qty_magento'       : fields.function(_product_qty_magento, method=True, type='float', string='Magento Stock'),
        'export_to_magento' : fields.boolean('Export to Magento'), 
        'product_lines'     : fields.one2many('product.lines', 'bundle_product_id','Item'), 
        'magento_pro_type' :fields.selection([('simple','Simple Product'),('bundle','Bundle Product')],'Magento Product Type'),  
       'default_code' : fields.char('Internal Reference', size=64, select=True),
       'magento_name':fields.char('Alias name at magento',size=256,help="Product Name at Magento"),
    }
    _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)', 'Internal Reference must be unique per Product!'),
    ]

    #creating index for searching records
    def _auto_init(self, cr, context=None):
        super(osv.osv, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'product_magneto_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX product_magneto_id ON product_product (magento_id)')
        
    
    _defaults = {
        'modified' : lambda *a: True,
        'magento_id' : lambda *a: -1,
        'export_to_magento' : lambda *a: False,
        'magento_pro_type' : 'simple'
    }
    
    #after modification in record, modified field should be True
    def write(self, cr, uid, ids, vals, context={}):
        if not vals.has_key('modified'):
            vals['modified'] = True
        return super(product_product, self).write(cr, uid, ids, vals, context)    
        
product_product()

# Categories Object Configuration
class product_category(osv.osv):
    _name = 'product.category'
    _inherit ='product.category'
    _columns = {
      'modified':fields.boolean('Modified since last synchronization'),
      'magento_id':fields.integer('Magento ID'),
      'update_to_magneto':fields.boolean('Update To Magneto'),
    }
    
    _defaults = {
        'modified': lambda *a: True,
        'magento_id': lambda *a: -1,
    }
    #after modification in record, modified field should be True
    def write(self, cr, uid, ids, vals, context={}):
        if not vals.has_key('modified'):
          vals['modified'] = True
        return super(product_category, self).write(cr, uid, ids, vals, context)    
product_category()

# Inherit Product Images class add fields based on magento
class product_images(osv.osv):
    _inherit = "product.images"
    _columns = {
        'base_image':fields.boolean('Base Image'),
        'small_image':fields.boolean('Small Image'),
        'thumbnail':fields.boolean('Thumbnail'),
        'exclude':fields.boolean('Exclude'),
        'position':fields.integer('Position'),
        'sync_status':fields.boolean('Sync Status', readonly=True),
        'modified':fields.boolean('Modified'),
        'file' : fields.char('file',size =512)
        
    }
    _defaults = {
        'sync_status':lambda * a: False,
        'base_image':lambda * a:False,
        'small_image':lambda * a:False,
        'thumbnail':lambda * a:False,
        'exclude':lambda * a:False,
        'modified':lambda * a:True,
    }
    
    def write(self, cr, uid, ids, vals, context={}):
        if not vals.has_key('modified'):
            vals['modified'] = True
        return super(product_images, self).write(cr, uid, ids, vals, context)
    
product_images()

class account_tax(osv.osv):
    _inherit="account.tax"
    _columns = {
                'magento_id':fields.integer('Magento Id',help="Give the magento id if this tax is used to export to magento"),
                }
#    _sql_constraints = [
#        ('magento_id_uniq', 'unique(magento_id)', 'Magento Id must be unique per Tax !'),
#    ]
account_tax()    
