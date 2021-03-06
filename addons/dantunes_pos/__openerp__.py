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


{
    'name': 'Dantunes Point of Sale',
    'version': '0.1',
    'category': '',
    'description': """ Creating Daily and Monthly report customizations for POS """,
    'author': 'Kiran & Nizam',
    'website': 'http://ktree.com',
    'depends': ['base','account','sale','point_of_sale','mail','base_calendar','product_variant_multi','stock','sale_stock'],
    'data': ['wizard/pos_report_wizard_view.xml','point_of_sale_view.xml','product_action_view.xml','sale_view.xml','product_view.xml','account_invoice_view.xml'],
    'demo': [],
    'test':[],
    'installable': True,
    'images': [],
}