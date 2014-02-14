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

import base64
import re
from openerp import tools

from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
                       'temp':fields.boolean('temp'),
                }
class mail_notification(osv.Model):
    """ Class holding notifications pushed to partners. Followers and partners
        added in 'contacts to notify' receive notifications. """
    _inherit = 'mail.notification'
    def get_partners_to_notify(self, cr, uid, message, partners_to_notify=None,context=None):
        """ Return the list of partners to notify, based on their preferences.

            :param browse_record message: mail.message to notify
        """
        notify_pids = []
        for notification in message.notification_ids:
            if notification.read:
                continue
            partner = notification.partner_id
            # Do not send to partners without email address defined
            if not partner.email:
                continue
            # Partner does not want to receive any emails
            if partner.notification_email_send == 'none':
                continue
            # Partner wants to receive only emails and comments
            if partner.notification_email_send == 'comment' and message.type not in ('email', 'comment'):
                continue
            # Partner wants to receive only emails
            if partner.notification_email_send == 'email' and message.type != 'email':
                continue
            if not partner.temp:
                  notify_pids.append(partner.id)
        return notify_pids
class mail_compose_message(osv.osv):
    _inherit = 'mail.compose.message'
    _columns = {
                       'boolean':fields.boolean("Don't Send email"),
                }
    _defaults = {
                 'boolean':True,
                 }
    def send_mail(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        if context is None:
            context = {}
        active_ids = context.get('active_ids')
   
       
        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mail_mode = wizard.composition_mode == 'mass_mail'
            active_model_pool = self.pool.get(wizard.model if wizard.model else 'mail.thread')
            prvious = self.pool.get('res.users').browse(cr,uid,uid).partner_id.id
            if wizard.boolean:
                self.pool.get('res.partner').write(cr,uid,[prvious],{'temp':True})
            else:
                   self.pool.get('res.partner').write(cr,uid,[prvious],{'temp':False})
            # wizard works in batch mode: [res_id] or active_ids
            res_ids = active_ids if mass_mail_mode and wizard.model and active_ids else [wizard.res_id]
            for res_id in res_ids:
                # default values, according to the wizard options
                post_values = {
                    'subject': wizard.subject,
                    'body': wizard.body,
                    'parent_id': wizard.parent_id and wizard.parent_id.id,
                    'partner_ids': [(4, partner.id) for partner in wizard.partner_ids],
                    'attachments': [(attach.datas_fname or attach.name, base64.b64decode(attach.datas)) for attach in wizard.attachment_ids],
                }
                # mass mailing: render and override default values
                if mass_mail_mode and wizard.model:
                    email_dict = self.render_message(cr, uid, wizard, res_id, context=context)
                    new_partner_ids = email_dict.pop('partner_ids', [])
                    post_values['partner_ids'] += [(4, partner_id) for partner_id in new_partner_ids]
                    new_attachments = email_dict.pop('attachments', [])
                    post_values['attachments'] += new_attachments
                    post_values.update(email_dict)
                # automatically subscribe recipients if asked to
                
                if context.get('mail_post_autofollow') and wizard.model and post_values.get('partner_ids'):
                    active_model_pool.message_subscribe(cr, uid, [res_id], [item[1] for item in post_values.get('partner_ids')], context=context)
                # post the message
                active_model_pool.message_post(cr, uid, [res_id], type='comment', subtype='mt_comment', context=context, **post_values)

            # post process: update attachments, because id is not necessarily known when adding attachments in Chatter
            # self.pool.get('ir.attachment').write(cr, uid, [attach.id for attach in wizard.attachment_ids], {
            #     'res_id': wizard.id, 'res_model': wizard.model or False}, context=context)

        return {'type': 'ir.actions.act_window_close'}

mail_compose_message()    