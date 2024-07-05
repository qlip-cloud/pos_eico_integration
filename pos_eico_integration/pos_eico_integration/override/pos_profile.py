import frappe
from frappe import _

from erpnext.accounts.doctype.pos_profile.pos_profile import POSProfile
from pos_eico_integration.pos_eico_integration.exception import common_exception

class EICOPOSProfile(POSProfile):

    def validate(self):

        if self.eico_sales_team:
            if sum([member.allocated_percentage or 0 for member in self.eico_sales_team]) != 100:
                frappe.throw(_("Total contribution percentage should be equal to 100"))
        else:
            common_exception.value_required_exception('Sales Team')

        return super(EICOPOSProfile, self).validate()