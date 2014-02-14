from osv import fields,osv
from pprint import pprint
#This file is used to store number of records imported/exported
class number_record_import_export(osv.osv):
   _name='number.record.import.export'
   _columns = {
        'name' :fields.text('Number Of Records'), 
 }
number_record_import_export()   