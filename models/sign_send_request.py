from odoo import api, fields, models
from odoo.exceptions import UserError

# 1. Modelo de los firmantes (aquí van los campos que se ven en la lista)
class SignSendRequestSigner(models.TransientModel):
    _inherit = 'sign.send.request.signer'

    is_employee = fields.Boolean(
        string='Es empleado',
        compute='_compute_is_employee',
        compute_sudo=True,
    )
    cc_personal_email = fields.Boolean(
        string='Copia a correo personal',
        help="Envía una copia del documento firmado al correo personal del empleado.",
    )

    def _get_signer_partners(self):
        self.ensure_one()
        if 'partner_ids' in self._fields:
            return self.partner_ids
        return self.partner_id

    @api.model
    def _find_employees(self, partners):
        if not partners:
            return self.env['hr.employee']
        Employee = self.env['hr.employee'].sudo()
        domain = [('user_id.partner_id', 'in', partners.ids)]
        if 'work_contact_id' in Employee._fields:
            domain = ['|', ('work_contact_id', 'in', partners.ids)] + domain
        return Employee.search(domain)

    @api.depends('partner_id', 'partner_ids') # Añadido partner_ids por si acaso
    def _compute_is_employee(self):
        for signer in self:
            partners = signer._get_signer_partners()
            signer.is_employee = bool(self._find_employees(partners))


# 2. Modelo principal de la solicitud (aquí va la lógica de envío)
class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    def _get_personal_copy_emails(self):
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

    def create_request(self, *args, **kwargs):
        # Guardamos los correos antes de llamar al método original
        emails = self._get_personal_copy_emails()
        
        # Llamamos al método original de Odoo
        res = super().create_request(*args, **kwargs)
        
        # Si hay correos, hacemos algo con ellos
        if emails:
            # OJO: Aquí es donde tendrías que implementar la lógica para enviar el correo
            # Por ahora, solo lo dejamos preparado para que no falle.
            # Ejemplo: self.env['mail.mail'].create({...})
            pass
            
        return res