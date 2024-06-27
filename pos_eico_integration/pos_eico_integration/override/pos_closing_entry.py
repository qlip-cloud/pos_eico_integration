import frappe

from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import POSClosingEntry
from pos_eico_integration.pos_eico_integration.exception import common_exception


class EICOPOSClosingEntry(POSClosingEntry):

    def on_cancel(self):

        common_exception.validate_on_cancel()
