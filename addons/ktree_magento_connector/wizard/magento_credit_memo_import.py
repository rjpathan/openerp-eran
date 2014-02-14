#This python file is used to call sale import wizard
#import wizard
import pooler
import os
from osv import osv, fields

class wizard_magneto_order_import(osv.osv_memory):
    _name = 'magneto.creditmemo.import'
    _description = 'Import credit memo'
    
    def do_creditmemo_import(self, cr, uid, ids, context=None):
        result=self.pool.get('magento.configuration').import_credit_memos(cr, uid)
        if (result < 0):
            raise osv.except_osv(('Warning'), ('Import failed, please refer to configure file for failure details.'))
        data_obj = self.pool.get('ir.model.data')
        if result >-1:
            text="%s Credit Memos Imported !" %result
            cust_text_ids=self.pool.get('number.record.import.export').search(cr, uid, [])
            for ids in cust_text_ids:
               self.pool.get('number.record.import.export').unlink(cr, uid, ids, context=None)
            self.pool.get('number.record.import.export').create(cr,uid,{'name':text,})
            xml_id='number_record_import_export_tree'
            res = data_obj.get_object_reference(cr, uid, 'ktree_magento_connector', xml_id)
            context.update({'view_id': res and res[1] or False})
            return {
                'name': 'No Of Records Import/Export',
                'view_type':'form',
                'view_mode':'tree',
                'res_model':'number.record.import.export',
                'type':'ir.actions.act_window',
                'context':context,
            }

wizard_magneto_order_import()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
