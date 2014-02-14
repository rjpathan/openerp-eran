# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2010-2011 Akretion (www.akretion.com). All Rights Reserved
#    @author Sebatien Beau <sebastien.beau@akretion.com>
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#       update to use a single "Generate/Update" button & price computation code
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
import netsvc
# Lib to eval python code with security
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _
from openerp import tools

LOGGER = netsvc.Logger()

#
# Dimensions Definition
#
class product_variant_dimension_type(osv.Model):
    _name = "product.variant.dimension.type"
    _description = "Dimension Type"

    _columns = {
        'description': fields.char('Description', size=64, translate=True),
        'name': fields.char('Dimension Type Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="The product 'variants' code will use this to order the dimension values"),
        'option_ids': fields.one2many('product.variant.dimension.option', 'dimension_id', 'Dimension Options'),
        'product_tmpl_id': fields.many2many('product.template', 'product_template_dimension_rel', 'dimension_id', 'template_id', 'Product Template'),
        'allow_custom_value': fields.boolean('Allow Custom Value', help="If true, custom values can be entered in the product configurator"),
        'mandatory_dimension': fields.boolean('Mandatory Dimension', help="If false, variant products will be created with and without this dimension"),
    }

    _defaults = {
        'mandatory_dimension': 1,
    }
    
    _order = "sequence, name"

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=None):
        if context is None:
            context = {}
        if not context.get('product_tmpl_id', False):
            args = None
        return super(product_variant_dimension_type, self).name_search(cr, user, '', args, 'ilike', None, None)

product_variant_dimension_type()

class product_variant_dimension_option(osv.Model):
    _name = "product.variant.dimension.option"
    _description = "Dimension Option"

    def _get_dimension_values(self, cr, uid, ids, context=None):
        return self.pool.get('product.variant.dimension.value').search(cr, uid, [('dimension_id', 'in', ids)], context=context)

    _columns = {
        'name': fields.char('Dimension Option Name', size=64, required=True),
        'code': fields.char('Code', size=64),
        'sequence': fields.integer('Sequence'),
        'dimension_id': fields.many2one('product.variant.dimension.type', 'Dimension Type', ondelete='cascade'),
    }

    _order = "dimension_id, sequence, name"

product_variant_dimension_option()


class product_variant_dimension_value(osv.Model):
    _name = "product.variant.dimension.value"
    _description = "Dimension Value"
    _rec_name = "option_id"

    def unlink(self, cr, uid, ids, context=None):
        for value in self.browse(cr, uid, ids, context=context):
            if value.product_ids:
                product_list = '\n    - ' + '\n    - '.join([product.name for product in value.product_ids])
                raise orm.except_orm(_('Dimension value can not be removed'), _("The value %s is used by the products : %s \n Please remove these products before removing the value." % (value.option_id.name, product_list)))
        return super(product_variant_dimension_value, self).unlink(cr, uid, ids, context)

    def _get_dimension_values(self, cr, uid, ids, context=None):
        return self.pool.get('product.variant.dimension.value').search(cr, uid, [('dimension_id', 'in', ids)], context=context)

    _columns = {
        'option_id' : fields.many2one('product.variant.dimension.option', 'Option', required=True),
        'name': fields.related('option_id', 'name', type='char', relation='product.variant.dimension.option', string="Dimension Value", readonly=True),
        'sequence' : fields.integer('Sequence'),
        'price_extra' : fields.float('Sale Price Extra', digits_compute=dp.get_precision('Sale Price')),
        'price_margin' : fields.float('Sale Price Margin', digits_compute=dp.get_precision('Sale Price')),
        'cost_price_extra' : fields.float('Cost Price Extra', digits_compute=dp.get_precision('Purchase Price')),
        'dimension_id' : fields.related('option_id', 'dimension_id', type="many2one", relation="product.variant.dimension.type", string="Dimension Type", store=True),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', ondelete='cascade'),
        'dimension_sequence': fields.related('dimension_id', 'sequence', string="Related Dimension Sequence",#used for ordering purposes in the "variants"
             store={
                'product.variant.dimension.type': (_get_dimension_values, ['sequence'], 10),
            }),
        'product_ids': fields.many2many('product.product', 'product_product_dimension_rel', 'dimension_id', 'product_id', 'Variant', readonly=True),
        'active' : fields.boolean('Active', help="If false, this value will not be used anymore to generate variants."),
    }

    _defaults = {
        'active': True,
    }

    _order = "dimension_sequence, sequence, option_id"
    
product_variant_dimension_value()

class product_variant_osv(osv.osv):
    _name='product.variant.osv'
    _duplicated_fields = ['name']

    def get_vals_to_write(self, vals):
        vals_to_write = {}
        for field in self._duplicated_fields:
            if field in vals.keys():
                vals_to_write[field] = vals[field]
        return vals_to_write


class product_template(osv.Model):
    _inherit = "product.template"
    _order = "name"
    
    
    _columns = {
        'dimension_type_ids':fields.many2many('product.variant.dimension.type', 'product_template_dimension_rel', 'template_id', 'dimension_id', 'Dimension Types'),
        'value_ids': fields.one2many('product.variant.dimension.value', 'product_tmpl_id', 'Dimension Values'),
        'variant_ids':fields.one2many('product.product', 'product_tmpl_id', 'Variants'),
        'variant_model_name':fields.char('Variant Model Name', size=64, required=True, help='[_o.dimension_id.name_] will be replaced by the name of the dimension and [_o.option_id.code_] by the code of the option. Example of Variant Model Name : "[_o.dimension_id.name_] - [_o.option_id.code_]"'),
        'variant_model_name_separator':fields.char('Variant Model Name Separator', size=64, help= 'Add a separator between the elements of the variant name'),
        'code_generator' : fields.char('Code Generator Text', size=64, help='enter the model for the product code, all parameter between [_o.my_field_] will be replace by the product field. Example product_code model : prefix_[_o.variants_]_suffixe ==> result : prefix_2S2T_suffix'),
        'code_generator_no' : fields.integer('Code Generator Number'),
        'is_multi_variants' : fields.boolean('Is Multi Variants'),
        'disable_neg':fields.boolean('Disable Negative Stock'),
        'export_to_magento':fields.boolean('Export To Magento'),
        'alias_name':fields.char('Alias Name',size=56),
        'shop':fields.selection([('web shop','Web Shop'),('konstanz','Konstanz'),('freiburg','Freiburg')],'Select Location'),
        'pos_category_id': fields.many2one('pos.category','Point of Sale Category'),
        'variant_track_production' : fields.boolean('Track Production Lots on variants ?'),
        'variant_track_incoming' : fields.boolean('Track Incoming Lots on variants ?'),
        'variant_track_outgoing' : fields.boolean('Track Outgoing Lots on variants ?'),
    }
    
    _defaults = {
        'variant_model_name': '[_o.dimension_id.name_] - [_o.option_id.name_]',
        'variant_model_name_separator': ' - ',
        'is_multi_variants' : False,
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context and context.get('unlink_from_product_product', False):
            for template in self.browse(cr, uid, ids, context):
                if not template.is_multi_variants and template.variant_ids:
                    super(product_template, self).unlink(cr, uid, [template.id], context)
        else:
            for template in self.browse(cr, uid, ids, context):
                self.pool.get('product.product').unlink(cr,uid,[i.id for i in template.variant_ids],context)
                super(product_template, self).unlink(cr, uid,ids, context)
        return True
    def create(self,cr,uid,vals,context=None):
        if context.has_key('name1'):
            vals['name']=context['name1']
        res_id=super(product_template,self).create(cr,uid,vals,context)
        return res_id
    def write(self, cr, uid, ids, vals, context=None):
        # When your write the name on a simple product from the menu product template you have to update the name on the product product
        # Two solution was posible overwritting the write function or overwritting the read function
        # I choose to overwrite the write function because read is call more often than the write function
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}

        res = super(product_template, self).write(cr, uid, ids, vals.copy(), context=context)

        if not context.get('iamthechild', False):
            obj_product = self.pool.get('product.product')
            if vals.get('is_multi_variants', 'wrong') != 'wrong':
                if vals['is_multi_variants']:
                    prod_tmpl_ids_simple = False
                else:
                    prod_tmpl_ids_simple = ids
            else:            
                prod_tmpl_ids_simple = self.search(cr, uid, [['id', 'in', ids], ['is_multi_variants', '=', False]], context=context)
            
            if prod_tmpl_ids_simple:
                #NB in the case that the user have just unchecked the option 'is_multi_variants' without changing any field the vals_to_write is empty
                vals_to_write = obj_product.get_vals_to_write(vals)
                if vals_to_write:
                    ctx = context.copy()
                    ctx['iamthechild'] = True
                    product_ids = obj_product.search(cr, uid, [['product_tmpl_id', 'in', prod_tmpl_ids_simple]])
                    obj_product.write(cr, uid, product_ids, vals_to_write, context=ctx)
        return res

    def add_all_option(self, cr, uid, ids, context=None):
        #Reactive all unactive values
        value_obj = self.pool.get('product.variant.dimension.value')
        for template in self.browse(cr, uid, ids, context=context):
            values_ids = value_obj.search(cr, uid, [['product_tmpl_id','=', template.id], '|', ['active', '=', False], ['active', '=', True]], context=context)
            value_obj.write(cr, uid, values_ids, {'active':True}, context=context)
            existing_option_ids = [value.option_id.id for value in value_obj.browse(cr, uid, values_ids,context=context)]
            vals = {'value_ids' : []}
            for dim in template.dimension_type_ids:
                for option in dim.option_ids:
                    if not option.id in existing_option_ids:
                        vals['value_ids'] += [[0, 0, {'option_id': option.id,'sequence':option.sequence}]]
            self.write(cr, uid, template.id, vals, context=context)    
        return True

    def get_products_from_product_template(self, cr, uid, ids, context=None):
        product_tmpl = self.read(cr, uid, ids, ['variant_ids'], context=context)
        return [id for vals in product_tmpl for id in vals['variant_ids']]
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'variant_ids':False,})
        return super(product_template, self).copy(cr, uid, id, default, context)

    def copy_translations(self, cr, uid, old_id, new_id, context=None):
        if context is None:
            context = {}
        # avoid recursion through already copied records in case of circular relationship
        seen_map = context.setdefault('__copy_translations_seen',{})
        if old_id in seen_map.setdefault(self._name,[]):
            return
        seen_map[self._name].append(old_id)
        return super(product_template, self).copy_translations(cr, uid, old_id, new_id, context=context)

    def _create_variant_list(self, cr, ids, uid, vals, context=None):
        
        def cartesian_product(args):
            if len(args) == 1: return [x and [x] or [] for x in args[0]]
            return [(i and [i] or []) + j for j in cartesian_product(args[1:]) for i in args[0]]
        res=cartesian_product(vals)
        return res

    def product_product_variants_vals(self, cr, uid, product_temp, variant, context=None):
        """Return Product Product Values Dicc
        :product_temp Object
        :variant list ids
        :return vals
        """

        vals = {}
        vals['track_production'] = product_temp.variant_track_production
        vals['track_incoming'] = product_temp.variant_track_incoming
        vals['track_outgoing'] = product_temp.variant_track_outgoing
        vals['product_tmpl_id'] = product_temp.id
        vals['taxes_id']=(6,0,product_temp.taxes_id)
        vals['supplier_taxes_id']=(6,0,product_temp.supplier_taxes_id)
        vals['property_account_income']=product_temp.property_account_income.id
        vals['property_account_expense']=product_temp.property_account_expense.id
        vals['dimension_value_ids'] = [(6,0,variant)]

        return vals
    
    def update_product_stock(self,cr,uid,ids,context=None):
        for pro in self.browse(cr,uid,ids[0]).variant_ids:
#            print pro.stock_value,'stock-------------'
#            lot_id=self.pool.get('stock.production.lot').create(cr,uid,{'product_id':pro.id})
            data={'new_quantity':pro.stock_value,'shop':pro.product_tmpl_id.shop}
            self.pool.get('product.product').change_product_qty(cr,uid,pro.id,data,context)
        return True

    def button_generate_variants(self, cr, uid, ids, context=None):
        """Generate Product Products from variants (product.template)
        :ids: list
        :return products (list of products)
        """
        if context is None:
            context = {}
        variants_obj = self.pool.get('product.product')
        temp_val_list = []

        for product_temp in self.browse(cr, uid, ids, context):
            #for temp_type in product_temp.dimension_type_ids:
            #    temp_val_list.append([temp_type_value.id for temp_type_value in temp_type.value_ids] + (not temp_type.mandatory_dimension and [None] or []))
                #TODO c'est quoi ça??
                # if last dimension_type has no dimension_value, we ignore it
            #    if not temp_val_list[-1]:
            #        temp_val_list.pop()
            res = {}
            for value in product_temp.value_ids:
                if res.get(value.dimension_id, False):
                    res[value.dimension_id] += [value.id]
                else:
                    res[value.dimension_id] = [value.id]
            ds={}
            for d in res:
                if ds.has_key(d.sequence):
                    ds[d.sequence]+=[d]
                else:
                    ds[d.sequence]=[d]
            dl=[]
            for s in ds:
                dl=ds[s]+dl
            for dim in dl:
                temp_val_list += [res[dim] + (not dim.mandatory_dimension and [None] or [])]
            if temp_val_list:
                list_of_variants = self._create_variant_list(cr, uid, ids, temp_val_list, context)
                existing_product_ids = variants_obj.search(cr, uid, [('product_tmpl_id', '=', product_temp.id)])
                existing_product_dim_value = variants_obj.read(cr, uid, existing_product_ids, ['dimension_value_ids'])
                list_of_variants_existing = [x['dimension_value_ids'] for x in existing_product_dim_value]
                for x in list_of_variants_existing:
                    x.sort()
                for x in list_of_variants:
                    x.sort()
                list_of_variants_to_create = [x for x in list_of_variants if not x in list_of_variants_existing]
                
                LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "variant existing : %s, variant to create : %s" % (len(list_of_variants_existing), len(list_of_variants_to_create)))
                count = 0
                for variant in list_of_variants_to_create:
                    count += 1
                    vals = self.product_product_variants_vals(cr, uid, product_temp, variant, context)
                    product_id = variants_obj.create(cr, uid, vals, {'generate_from_template' : True})
                    if count%50 == 0:
                        cr.commit()
                        LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "product created : %s" % (count,))
                LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "product created : %s" % (count,))

        product_ids = self.get_products_from_product_template(cr, uid, ids, context=context)

        # FIRST, Generate/Update variant names ('variants' field)
        LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "Starting to generate/update variant names...")
        self.pool.get('product.product').build_variants_name(cr, uid, product_ids, context=context)
        LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "End of the generation/update of variant names.")
        # SECOND, Generate/Update product codes and properties (we may need variants name for that)
        LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "Starting to generate/update product codes and properties...")
        self.pool.get('product.product').build_product_code_and_properties(cr, uid, product_ids, context=context)
        LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_INFO, "End of the generation/update of product codes and properties.")
        LOGGER.notifyChannel('product_variant_multi_advanced', netsvc.LOG_INFO, "Starting to generate/update product names...")

        context['variants_values'] = {}
        for product in self.pool.get('product.product').read(cr, uid, product_ids, ['variants'], context=context):
            context['variants_values'][product['id']] = product['variants']
        self.pool.get('product.product').build_product_name(cr, uid, product_ids, context=context)
        LOGGER.notifyChannel('product_variant_multi_advanced', netsvc.LOG_INFO, "End of generation/update of product names.")
        
        return product_ids
        
product_template()


class product_product(osv.Model):
    _inherit = "product.product"
    _duplicated_fields = ['name','taxes_id','supplier_taxes_id','property_account_income','property_account_expense']
    code_no=0
    def init(self, cr):
        #For the first installation if you already have product in your database the name of the existing product will be empty, so we fill it
        cr.execute("update product_product set name=name_template where name is null;")
        return True
  
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context['unlink_from_product_product']=True
        return super(product_product, self).unlink(cr, uid, ids, context)

    def build_product_name(self, cr, uid, ids, context=None):
        return self.build_product_field(cr, uid, ids, 'name', context=None)

    def build_product_field(self, cr, uid, ids, field, context=None):
        if context is None:
            context = {}
        def get_description_sale(product):
            return self.parse(cr, uid, product, product.product_tmpl_id.description_sale, context=context)

        def get_name(product):
            if context.get('variants_values', False):
                return (product.product_tmpl_id.name or '' )+ ' ' + (context['variants_values'][product.id] or '')
            return (product.product_tmpl_id.name or '' )+ ' ' + (product.variants or '')

        context['is_multi_variants']=True
        obj_lang=self.pool.get('res.lang')
        lang_ids = obj_lang.search(cr, uid, [('translatable','=',True)], context=context)
        lang_code = [x['code'] for x in obj_lang.read(cr, uid, lang_ids, ['code'], context=context)]
        for code in lang_code:
            context['lang'] = code
            for product in self.browse(cr, uid, ids, context=context):
                new_field_value = eval("get_" + field + "(product)") # TODO convert to safe_eval
                cur_field_value = safe_eval("product." + field, {'product': product})
                if new_field_value != cur_field_value:
                    self.write(cr, uid, product.id, {field: new_field_value}, context=context)
        return True


    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        context['from_pro']=1
        res = super(product_product, self).write(cr, uid, ids, vals.copy(), context=context)

        ids_simple = self.search(cr, uid, [['id', 'in', ids], ['is_multi_variants', '=', False]], context=context)

        if not context.get('iamthechild', False) and ids_simple:
            vals_to_write = self.get_vals_to_write(vals)
            if vals_to_write:
                obj_tmpl = self.pool.get('product.template')
                ctx = context.copy()
                ctx['iamthechild'] = True
                tmpl_ids = obj_tmpl.search(cr, uid, [['variant_ids', 'in', ids_simple]])
                obj_tmpl.write(cr, uid, tmpl_ids, vals_to_write, context=ctx)
        return res

    def create(self, cr, uid, vals, context=None):
        #TAKE CARE for inherits objects openerp will create firstly the product_template and after the product_product
        # and so the duplicated fields (duplicated field = field which are on the template and on the variant) will be on the product_template and not on the product_product
        #Also when a product is created the duplicated field are empty for the product.product, this is why the field name can not be a required field
        #This should be fix in the orm in the future
        if context is None:
            context = {}
        if vals.has_key('name'):
            context['name1']=vals['name']
        ids = super(product_product, self).create(cr, uid, vals.copy(), context=context) #using vals.copy() if not the vals will be changed by calling the super method
        ####### write the value in the product_product
        ctx = context.copy()
        ctx['iamthechild'] = True
        vals_to_write = self.get_vals_to_write(vals)
        if vals_to_write:
            self.write(cr, uid, ids, vals_to_write, context=ctx)
        return ids



    def parse(self, cr, uid, o, text, context=None):
        if not text:
            return ''
        vals = text.split('[_')
        description = ''
        for val in vals:
            if '_]' in val:
                sub_val = val.split('_]')
                try:
                    description += (safe_eval(sub_val[0], {'o' :o, 'context':context}) or '' ) + sub_val[1]
                except:
                    LOGGER.notifyChannel('product_variant_multi', netsvc.LOG_ERROR, "%s can't eval. Description is blank" % (sub_val[0]))
                    description += ''
            else:
                if context.has_key('code_gen'):
                    description += (val.strip()+format(self.code_no,'02d'))
                    self.code_no+=1
                else:
                    description += val
        return description


    def generate_product_code(self, cr, uid, product_obj, code_generator, context=None):
        '''I wrote this stupid function to be able to inherit it in a custom module !'''
        context['code_gen']=1
        return self.parse(cr, uid, product_obj, code_generator, context=context)
    
    def change_product_qty(self, cr, uid, ids,data,context=None):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        loc_id=self.pool.get('stock.location').search(cr,uid,[('name','ilike',data['shop'])])
        rec_id = ids
        inventry_obj = self.pool.get('stock.inventory')
        inventry_line_obj = self.pool.get('stock.inventory.line')
        prod_obj_pool = self.pool.get('product.product')

        res_original = prod_obj_pool.browse(cr, uid, rec_id, context=context)
        if data['new_quantity'] < 0:
            raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))
        if data['new_quantity'] >= 0:
            inventory_id = inventry_obj.create(cr , uid, {'name': _('INV: %s') % tools.ustr(res_original.name)}, context=context)
            line_data ={
                'inventory_id' : inventory_id,
                'product_qty' : data['new_quantity'],
                'location_id' : loc_id and loc_id[0] or '',
                'product_id' : rec_id,
                'product_uom' : res_original.uom_id.id,
                'prod_lot_id' : False
            }
            inventry_line_obj.create(cr , uid, line_data, context=context)
    
            inventry_obj.action_confirm(cr, uid, [inventory_id], context=context)
            inventry_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}

    def build_product_code_and_properties(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        flag = False
        for product in self.browse(cr, uid, ids, context=context):
            if not flag:
                self.code_no=product.product_tmpl_id.code_generator_no
                flag=True
            new_default_code = self.generate_product_code(cr, uid, product, product.product_tmpl_id.code_generator, context=context)
            current_values = {
                'default_code': product.default_code,
                'check_box':product.check_box,
                'pos_categ_id':product.pos_categ_id.id,
                'export_to_magento':product.export_to_magento,
                'taxes_id':[(6,0,[i.id for i in product.taxes_id])],
                'supplier_taxes_id':[(6,0,[i.id for i in product.supplier_taxes_id])],
                'property_account_income':product.property_account_income.id,
		        'magento_attr_id':product.magento_attr_id,
                'property_account_expense':product.property_account_expense.id,
                'magento_name':product.magento_name
#                'track_production': product.track_production,
#                'track_outgoing': product.track_outgoing,
#                'track_incoming': product.track_incoming,
            }
            new_values = {
                'default_code': new_default_code,
                'check_box':product.product_tmpl_id.disable_neg,
                'pos_categ_id':product.product_tmpl_id.pos_category_id.id,
                'export_to_magento':product.product_tmpl_id.export_to_magento,
                'taxes_id':[(6,0,[i.id for i in product.product_tmpl_id.taxes_id])],
                'supplier_taxes_id':[(6,0,[i.id for i in product.product_tmpl_id.supplier_taxes_id])],
                'property_account_income':product.product_tmpl_id.property_account_income.id,
                'property_account_expense':product.product_tmpl_id.property_account_expense.id,
		'magento_attr_id':product.product_tmpl_id.magento_attr_id,
                'magento_name':product.product_tmpl_id.alias_name,
#                'track_production': product.product_tmpl_id.variant_track_production,
#                'track_outgoing': product.product_tmpl_id.variant_track_outgoing,
#                'track_incoming': product.product_tmpl_id.variant_track_incoming,
            }
            if new_values != current_values:
                self.write(cr, uid, product.id, new_values, context=context)
        return True

    def product_ids_variant_changed(self, cr, uid, ids, res, context=None):
        '''it's a hook for product_variant_multi advanced'''
        return True

    def generate_variant_name(self, cr, uid, product_id, context=None):
        '''Do the generation of the variant name in a dedicated function, so that we can
        inherit this function to hack the code generation'''
        if context is None:
            context = {}
        product = self.browse(cr, uid, product_id, context=context)
        model = product.variant_model_name
        r = map(lambda dim: [dim.dimension_id.sequence ,self.parse(cr, uid, dim, model, context=context)], product.dimension_value_ids)
        r.sort()
        r = [x[1] for x in r]
        new_variant_name = (product.variant_model_name_separator or '').join(r)
        return new_variant_name


    def build_variants_name(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            new_variant_name = self.generate_variant_name(cr, uid, product.id, context=context)
            if new_variant_name != product.variants:
                self.write(cr, uid, product.id, {'variants': new_variant_name}, context=context)
        return True

    def _check_dimension_values(self, cr, uid, ids): # TODO: check that all dimension_types of the product_template have a corresponding dimension_value ??
        for p in self.browse(cr, uid, ids, {}):
            buffer = []
            for value in p.dimension_value_ids:
                buffer.append(value.dimension_id)
            unique_set = set(buffer)
            if len(unique_set) != len(buffer):
                raise orm.except_orm(_('Constraint error :'), _("On product '%s', there are several dimension values for the same dimension type.") % p.name)
        return True

    def compute_product_dimension_extra_price(self, cr, uid, product_id, product_price_extra=False, dim_price_margin=False, dim_price_extra=False, context=None):
        if context is None:
            context = {}
        dimension_extra = 0.0
        product = self.browse(cr, uid, product_id, context=context)
        for dim in product.dimension_value_ids:
            if product_price_extra and dim_price_margin and dim_price_extra:
                dimension_extra += safe_eval('product.' + product_price_extra, {'product': product}) * safe_eval('dim.' + dim_price_margin, {'dim': dim}) + safe_eval('dim.' + dim_price_extra, {'dim': dim})
            elif not product_price_extra and not dim_price_margin and dim_price_extra:
                dimension_extra += safe_eval('dim.' + dim_price_extra, {'dim': dim})
            elif product_price_extra and dim_price_margin and not dim_price_extra:
                dimension_extra += safe_eval('product.' + product_price_extra, {'product': product}) * safe_eval('dim.' + dim_price_margin, {'dim': dim})
            elif product_price_extra and not dim_price_margin and dim_price_extra:
                dimension_extra += safe_eval('product.' + product_price_extra, {'product': product}) + safe_eval('dim.' + dim_price_extra, {'dim': dim})

        if 'uom' in context:
            product_uom_obj = self.pool.get('product.uom')
            uom = product.uos_id or product.uom_id
            dimension_extra = product_uom_obj._compute_price(cr, uid,
                uom.id, dimension_extra, context['uom'])
        return dimension_extra


    def compute_dimension_extra_price(self, cr, uid, ids, result, product_price_extra=False, dim_price_margin=False, dim_price_extra=False, context=None):
        if context is None:
            context = {}
        for product in self.browse(cr, uid, ids, context=context):
            dimension_extra = self.compute_product_dimension_extra_price(cr, uid, product.id, product_price_extra=product_price_extra, dim_price_margin=dim_price_margin, dim_price_extra=dim_price_extra, context=context)
            result[product.id] += dimension_extra
        return result

    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        if context is None:
            context = {}
        result = super(product_product, self).price_get(cr, uid, ids, ptype, context=context)
        if ptype == 'list_price': #TODO check if the price_margin on the dimension is very usefull, maybe we will remove it
            result = self.compute_dimension_extra_price(cr, uid, ids, result, product_price_extra='price_extra', dim_price_margin='price_margin', dim_price_extra='price_extra', context=context)

        elif ptype == 'standard_price':
            result = self.compute_dimension_extra_price(cr, uid, ids, result, product_price_extra='cost_price_extra', dim_price_extra='cost_price_extra', context=context)
        return result
    
    def get_vals_to_write(self, vals):
        vals_to_write = {}
        for field in self._duplicated_fields:
            if field in vals.keys():
                vals_to_write[field] = vals[field]
        return vals_to_write

    def _product_lst_price(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = super(product_product, self)._product_lst_price(cr, uid, ids, name, arg, context=context)
        result = self.compute_dimension_extra_price(cr, uid, ids, result, product_price_extra='price_extra', dim_price_margin='price_margin', dim_price_extra='price_extra', context=context)
        return result


    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'variant_ids':False,})
        return super(product_product, self).copy(cr, uid, id, default, context)

    def _product_compute_weight_volume(self, cr, uid, ids, fields, arg, context=None):
        result = {}
        # print 'compute', ids, fields, context
        for product in self.browse(cr, uid, ids, context=context):
            result[product.id]={}
            result[product.id]['total_weight'] =  product.weight + product.additional_weight
            result[product.id]['total_weight_net'] =  product.weight_net + product.additional_weight_net
            result[product.id]['total_volume'] = product.volume + product.additional_volume
        return result

    _columns = {
        'name': fields.char('Name', size=128, select=True),
        'taxes_id': fields.many2many('account.tax', 'pro_product_taxes_rel',
            'prod_id', 'tax_id', 'Customer Taxes',
            domain=[('parent_id','=',False),('type_tax_use','in',['sale','all'])]),
        'supplier_taxes_id': fields.many2many('account.tax',
            'pro_product_supplier_taxes_rel', 'prod_id', 'tax_id',
            'Supplier Taxes', domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])]),
        'property_account_income': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account",
            view_load=True,
            help="This account will be used for invoices instead of the default one to value sales for the current product."),
        'property_account_expense': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account",
            view_load=True,
            help="This account will be used for invoices instead of the default one to value expenses for the current product."),
        'dimension_value_ids': fields.many2many('product.variant.dimension.value', 'product_product_dimension_rel', 'product_id','dimension_id', 'Dimensions', domain="[('product_tmpl_id','=',product_tmpl_id)]"),
        'cost_price_extra' : fields.float('Purchase Extra Cost', digits_compute=dp.get_precision('Purchase Price')),
        'lst_price' : fields.function(_product_lst_price, method=True, type='float', string='List Price', digits_compute=dp.get_precision('Sale Price')),
        #the way the weight are implemented are not clean at all, we should redesign the module product form the addons in order to get something correclty.
        #indeed some field of the template have to be overwrited like weight, name, weight_net, volume.
        #in order to have a consitent api we should use the same field for getting the weight, now we have to use "weight" or "total_weight" not clean at all with external syncronization
        'total_weight': fields.function(_product_compute_weight_volume, method=True, type='float', string='Total Gross Weight', help="The gross weight in Kg.", multi='weight_volume'),
        'total_weight_net': fields.function(_product_compute_weight_volume, method=True, type='float', string='Total Net Weight', help="The net weight in Kg.", multi='weight_volume'),
        'total_volume':  fields.function(_product_compute_weight_volume, method=True, type='float', string='Total Volume', help="The volume in m3.", multi='weight_volume'),
        'additional_weight': fields.float('Additional Gross weight', help="The additional gross weight in Kg."),
        'additional_weight_net': fields.float('Additional Net weight', help="The additional net weight in Kg."),
        'additional_volume': fields.float('Additional Volume', help="The additional volume in Kg."),
        'stock_value':fields.integer('Amount Of Stock'),
        
    }
    _constraints = [ (_check_dimension_values, 'Several dimension values for the same dimension type', ['dimension_value_ids']),]

product_product()
