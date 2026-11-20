from odoo import Command, fields, models


class SignRequest(models.Model):
    _inherit = 'sign.request'

    personal_copy_emails = fields.Text(
        string='Copia a correos personales',
        copy=False,
        groups='sign.group_sign_user',
        help='Correos personales de empleados que recibirán el documento firmado.',
    )
    personal_copy_sent = fields.Boolean(copy=False)

    def send_completed_document(self, *args, **kwargs):
        res = super().send_completed_document(*args, **kwargs)
        self._send_personal_copy()
        return res

    # En algunas versiones el método lleva guion bajo; si el padre no lo define,
    # sign nunca lo invoca y este override queda inofensivo.
    def _send_completed_document(self, *args, **kwargs):
        res = super()._send_completed_document(*args, **kwargs)
        self._send_personal_copy()
        return res

    def _send_personal_copy(self):
        for request in self.sudo():
            if (request.personal_copy_sent or not request.personal_copy_emails
                    or not request.completed_document):
                continue
            name = '%s.pdf' % (request.reference or request.display_name or 'documento')
            attachment = self.env['ir.attachment'].sudo().create({
                'name': name,
                'datas': request.completed_document,
                'mimetype': 'application/pdf',
                'res_model': 'sign.request',
                'res_id': request.id,
            })
            company = request.create_uid.company_id or self.env.company
            mail = self.env['mail.mail'].sudo().create({
                'subject': 'Documento firmado: %s' % (request.reference or name),
                'body_html': (
                    '<p>Adjuntamos una copia del documento firmado '
                    '<strong>%s</strong>.</p>' % (request.reference or name)),
                'email_from': request.create_uid.email_formatted or company.email_formatted,
                'email_to': request.personal_copy_emails,
                'attachment_ids': [Command.link(attachment.id)],
                'auto_delete': True,
            })
            mail.send()
            request.personal_copy_sent = True
