from odoo import api, fields, models
from odoo.exceptions import UserError


class SignSendRequestSigner(models.TransientModel):
    _inherit = 'sign.send.request.signer'

    is_employee = fields.Boolean(
        string='Es empleado',
        compute='_compute_is_employee',
        compute_sudo=True,
    )
    cc_personal_email = fields.Boolean(
        string='Copia a correo personal',
        help="Envía una copia del documento firmado al correo personal del "
             "empleado (campo 'Correo electrónico' de la pestaña Personal), "
             "sin necesidad de crear un contacto adicional.",
    )

    def _get_signer_partners(self):
        """Compatible con líneas de un solo contacto (partner_id) o de varios (partner_ids)."""
        self.ensure_one()
        if 'partner_ids' in self._fields:
            return self.partner_ids
        return self.partner_id

    @api.model
    def _find_employees(self, partners):
        """Empleados vinculados a los contactos dados (contacto de trabajo o usuario)."""
        if not partners:
            return self.env['hr.employee']
        Employee = self.env['hr.employee'].sudo()
        domain = [('user_id.partner_id', 'in', partners.ids)]
        if 'work_contact_id' in Employee._fields:
            domain = ['|', ('work_contact_id', 'in', partners.ids)] + domain
        return Employee.search(domain)

    @api.depends('partner_id')
    def _compute_is_employee(self):
        for signer in self:
            partners = signer._get_signer_partners()
            signer.is_employee = bool(self._find_employees(partners))


class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    def _get_personal_copy_emails(self):
        """Correos personales de los firmantes marcados. Valida que existan."""
        emails = []
        for signer in self.signer_ids.filtered('cc_personal_email'):
            employees = self.env['sign.send.request.signer']._find_employees(
                signer._get_signer_partners())
            for employee in employees:
                email = (employee.private_email or '').strip()
                if not email:
                    raise UserError(
                        "El empleado %s no tiene correo personal configurado "
                        "(pestaña Personal)." % employee.name)
                if email not in emails:
                    emails.append(email)
        return emails

    @api.model
    def _to_sign_request(self, res):
        """create_request puede devolver un recordset, un dict o un id según la versión."""
        if isinstance(res, models.BaseModel):
            return res
        if isinstance(res, dict):
            return self.env['sign.request'].browse(res.get('id'))
        return self.env['sign.request'].browse(res)

    def create_request(self, *args, **kwargs):
        emails = self._get_personal_copy_emails()
        res = super().create_request(*args, **kwargs)
        if emails:
            request = self._to_sign_request(res)
            if request:
                request.sudo().write({'personal_copy_emails': ', '.join(emails)})
        return res
