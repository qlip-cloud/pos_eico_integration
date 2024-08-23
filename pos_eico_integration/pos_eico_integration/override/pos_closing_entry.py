import frappe

from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import POSClosingEntry
from pos_eico_integration.pos_eico_integration.override.pos_invoice_merge_log import pos_eico_consolidate_pos_invoices
from pos_eico_integration.pos_eico_integration.exception import common_exception


class EICOPOSClosingEntry(POSClosingEntry):

    def on_submit(self):

        pos_eico_consolidate_pos_invoices(closing_entry=self)

    def on_cancel(self):

        common_exception.validate_on_cancel()

    @frappe.whitelist()
    def retry(self):

        try:

            pos_eico_consolidate_pos_invoices(closing_entry=self)

            res = {
                'status': 200,
                'msg': self.name
            }

        except Exception as e:

            res = {
                'status': 500,
                'msg': str(e)
            }

        return res