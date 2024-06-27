import frappe
from frappe.utils import getdate
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import POSInvoiceMergeLog
from pos_eico_integration.pos_eico_integration.exception import common_exception


class EICOPOSInvoiceMergeLog(POSInvoiceMergeLog):

    def process_merging_into_sales_invoice(self, data):

        sales_invoice = self.get_new_sales_invoice()

        sales_invoice = self.merge_pos_invoice_into(sales_invoice, data)

        self.get_serie_sales_invoice('eico_series', sales_invoice)

        sales_invoice.is_consolidated = 1
        sales_invoice.set_posting_time = 1
        sales_invoice.posting_date = getdate(self.posting_date)
        sales_invoice.save()
        sales_invoice.submit()

        self.consolidated_invoice = sales_invoice.name

        return sales_invoice.name

    def process_merging_into_credit_note(self, data):

        credit_note = self.get_new_sales_invoice()

        credit_note.is_return = 1

        credit_note = self.merge_pos_invoice_into(credit_note, data)

        self.get_serie_sales_invoice('eico_series_credit_note', credit_note)

        credit_note.is_consolidated = 1
        credit_note.set_posting_time = 1
        credit_note.posting_date = getdate(self.posting_date)
        # TODO: return could be against multiple sales invoice which could also have been consolidated?
        # credit_note.return_against = self.consolidated_invoice
        credit_note.save()
        credit_note.submit()

        self.consolidated_credit_note = credit_note.name

        return credit_note.name

    def get_serie_sales_invoice(self, serie_field, sales_invoice_obj):
        
        pos_profile = frappe.get_value('POS Closing Entry', self.pos_closing_entry, 'pos_profile')

        if pos_profile:
            pos_profile_serie = frappe.get_value('POS Profile', pos_profile, serie_field)
            if pos_profile_serie:
                sales_invoice_obj.naming_series = pos_profile_serie
                sales_invoice_obj.eico_service_type = frappe.get_value('POS Profile', pos_profile, 'eico_service_type')

                if abs(sales_invoice_obj.get('discount_amount', 0)) > 0:
                    sales_invoice_obj.eico_discount_type = frappe.get_value('POS Profile', pos_profile, 'eico_discount_type')

                if sales_invoice_obj.is_return == 1:

                    data_json = frappe.db.get_values(
                        "POS Profile",
                        pos_profile,
                        ["eico_document_type_cn", "eico_payment_type_nc", "eico_payment_term_nc", "eico_note_concept", "eico_description_note_concept"],
                        as_dict=True)[0]
                    sales_invoice_obj.eico_document_type = data_json.eico_document_type_cn
                    sales_invoice_obj.eico_payment_type = data_json.eico_payment_type_nc
                    sales_invoice_obj.eico_payment_term = data_json.eico_payment_term_nc
                    sales_invoice_obj.eico_note_concept = data_json.eico_note_concept
                    sales_invoice_obj.eico_description_note_concept = data_json.eico_description_note_concept

                    if not sales_invoice_obj.return_against:
                        sales_invoice_obj.eico_per_fini = getdate(self.posting_date)
                        sales_invoice_obj.eico_per_ffin = getdate(self.posting_date)

                else:
                    data_json = frappe.db.get_values(
                        "POS Profile",
                        pos_profile,
                        ["eico_document_type", "eico_payment_type", "eico_payment_term"],
                        as_dict=True)[0]
                    sales_invoice_obj.eico_document_type = data_json.eico_document_type
                    sales_invoice_obj.eico_payment_type = data_json.eico_payment_type
                    sales_invoice_obj.eico_payment_term = data_json.eico_payment_term

            else:
                common_exception.value_required_exception(serie_field)
        else:
            common_exception.value_required_exception('pos_profile')
