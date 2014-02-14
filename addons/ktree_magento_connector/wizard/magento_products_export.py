#This python file is used to call product export wizard
import pooler
#import wizard
import os
from osv import osv, fields

class wizard_magneto_product_export(osv.osv_memory):
    _name = 'magneto.products.export'
    _description = 'Export Product'

    def do_products_export(self, cr, uid, ids, context=None):
        result1=self.pool.get('magento.configuration').export_categories(cr, uid)
        text1=''
        if result1>-1:
           text1="%s Category Exported!" %result1 
        result=self.pool.get('magento.configuration').export_products(cr, uid)  
        if (result < 0):
            raise osv.except_osv(('Warning'), ('Export failed, please refer to configure file for failure details.'))
        data_obj = self.pool.get('ir.model.data')
        if result >-1:
            text2="%s Product Exported !" %result
            if text1:
               text=str(text1)+','+str(text2)
            else:
               text=text2    
            cust_text_ids=self.pool.get('number.record.import.export').search(cr, uid, [])
            for ids in cust_text_ids:
               self.pool.get('number.record.import.export').unlink(cr, uid, ids, context=None)
            self.pool.get('number.record.import.export').create(cr,uid,{'name':text,})
            xml_id='number_record_import_export_tree'
            res = data_obj.get_object_reference(cr, uid, 'ktree_magento_connector', xml_id)
            context.update({'view_id': res and res[1] or False})
            return {
                'name': 'No Of Records Export',
                'view_type':'form',
                'view_mode':'tree',
                'res_model':'number.record.import.export',
                'type':'ir.actions.act_window',
                'context':context,
            }

wizard_magneto_product_export()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
