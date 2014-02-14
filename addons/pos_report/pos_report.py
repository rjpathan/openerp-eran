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

from openerp import tools
from openerp.osv import fields,osv

class pos_order_report(osv.osv):
    _name = "report.pos.order.extended"
    _description = "Point of Sale Orders Statistics"
    _auto = False
    _columns = {
        'date': fields.date('Date Order', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'supplier':fields.char('Supplier', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'state': fields.selection([('draft', 'New'), ('paid', 'Closed'), ('done', 'Synchronized'), ('invoiced', 'Invoiced'), ('cancel', 'Cancelled')],
                                  'Status'),
        'user_id':fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total':fields.float('Total Price', readonly=True),
        'margin':fields.float('Margin', readonly=True),
        'total_discount':fields.float('Total Discount', readonly=True),
        'average_price': fields.float('Average Price', readonly=True,group_operator="avg"),
        'shop_id':fields.many2one('sale.shop', 'Shop', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'nbr':fields.integer('# of Lines', readonly=True),
        'product_qty':fields.integer('# of Qty', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'delay_validation': fields.integer('Delay Validation'),
        'template_id': fields.integer('Template ID', readonly=True),
        'dimension_id': fields.many2one('product.variant.dimension.type', 'Dimension Type', readonly=True),
        'pvdo_id': fields.many2one('product.variant.dimension.option', 'Dimension Option', readonly=True),
        'multi_variants': fields.boolean('Dimension Option', readonly=True),
    }
    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_pos_order_extended')
        cr.execute("""
            create or replace view report_pos_order_extended as (
                select 
                    min(l.id) as id,
                    count(*) as nbr,
                    to_date(to_char(s.date_order, 'dd-MM-YYYY'),'dd-MM-YYYY') as date,
                    sum(l.qty * u.factor) as product_qty,
                    sum(l.qty * l.price_unit) as price_total,
                    sum(pt.list_price - pt.standard_price) as margin,
                    sum((l.qty * l.price_unit) * (l.discount / 100)) as total_discount,
                    to_char(s.date_order, 'YYYY') as year,
                    to_char(s.date_order, 'MM') as month,
                    to_char(s.date_order, 'YYYY-MM-DD') as day,
                    s.partner_id as partner_id,
                    rp.name as supplier,
                    s.state as state,
                    s.user_id as user_id,
                    s.shop_id as shop_id,
                    s.company_id as company_id,
                    s.sale_journal as journal_id,
                    l.product_id as product_id,
                    pt.id as template_id,
                    ptdr.dimension_id as dimension_id,
                    pvdo.id as pvdo_id,
                    pt.is_multi_variants as multi_variants
                from pos_order_line as l
                    left join pos_order s on (s.id=l.order_id)
                    left join product_product p on (l.product_id=p.id)
                    left join product_template pt on (pt.id=p.product_tmpl_id)
                    left join product_template_dimension_rel ptdr on (ptdr.template_id=p.product_tmpl_id)
                    left join product_variant_dimension_option pvdo on (pvdo.dimension_id=ptdr.dimension_id)
                    left join product_uom u on (u.id=pt.uom_id)
                    left join product_supplierinfo psi on (l.product_id=psi.product_id)
                    left join res_partner rp on (psi.name = rp.id)
                group by
                    s.date_order,
                    s.partner_id,
                    rp.name,
                    s.state,
                    s.user_id,
                    s.shop_id,
                    s.company_id,
                    s.sale_journal,
                    l.product_id,
                    s.create_date, pt.id,
                    ptdr.dimension_id,
                    pvdo.id
                having
                    sum(l.qty * u.factor) != 0)""")

pos_order_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
