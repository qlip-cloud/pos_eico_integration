from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, getdate, nowdate
from frappe.utils.background_jobs import enqueue
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
    POSInvoiceMergeLog, get_invoice_customer_map, get_all_unconsolidated_invoices,
    check_scheduler_status, job_already_enqueued, safe_load_json)
from electronic_invoicing_colombia.electronic_invoicing_colombia.uses_cases.sales_invoices.update import assert_is_not_wait_response
from pos_eico_integration.pos_eico_integration.exception import common_exception
import six


class EICOPOSInvoiceMergeLog(POSInvoiceMergeLog):

    def create_invoices(self):

        pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

        returns = [d for d in pos_invoice_docs if d.get('is_return') == 1]
        sales = [d for d in pos_invoice_docs if d.get('is_return') == 0]

        sales_invoice, credit_note = "", ""
        if returns:
            credit_note = self.process_merging_into_credit_note(returns)

        if sales:
            sales_invoice = self.process_merging_into_sales_invoice(sales)

        self.save() # save consolidated_sales_invoice & consolidated_credit_note ref in merge log

    def submit_invoices(self):

        self.process_submit_invoices(self.consolidated_credit_note)

        self.process_submit_invoices(self.consolidated_invoice)

    def process_submit_invoices(self, sales_inv_name):
        if sales_inv_name:
            si_doc = frappe.get_doc("Sales Invoice", sales_inv_name)
            if si_doc.status == 'Draft':
                si_doc.submit()
                frappe.db.commit()

    def on_submit(self):

        pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

        status_fv = self.consolidated_invoice and frappe.get_value("Sales Invoice", self.consolidated_invoice, ['status']) or ''
        status_nc = self.consolidated_credit_note and frappe.get_value("Sales Invoice", self.consolidated_credit_note, ['status']) or ''

        if (status_nc in ('Draft', 'Cancelled')) or status_fv in ('Draft', 'Cancelled'):
            frappe.throw(_("The invoice is in Draft/Cancelled. Please check"))

        self.update_pos_invoices(pos_invoice_docs, self.consolidated_invoice, self.consolidated_credit_note)

    def process_merging_into_sales_invoice(self, data):

        sales_invoice = self.get_new_sales_invoice()

        sales_invoice = self.merge_pos_invoice_into(sales_invoice, data)

        self.get_serie_sales_invoice('eico_series', sales_invoice)

        sales_invoice.is_consolidated = 1
        sales_invoice.set_posting_time = 1
        sales_invoice.posting_date = getdate(self.posting_date)
        sales_invoice.save()

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

        self.consolidated_credit_note = credit_note.name

        return credit_note.name

    def get_serie_sales_invoice(self, serie_field, sales_invoice_obj):
        
        pos_profile = frappe.get_value('POS Closing Entry', self.pos_closing_entry, 'pos_profile')

        if pos_profile:

            pos_profile_serie_obj = frappe.get_doc("POS Profile", pos_profile)
            pos_profile_serie = pos_profile_serie_obj.get(serie_field, None)
            if pos_profile_serie:
                sales_invoice_obj.naming_series = pos_profile_serie
                sales_invoice_obj.eico_service_type = pos_profile_serie_obj.get('eico_service_type')

                sales_invoice_obj.tax_id = frappe.get_value('Customer', sales_invoice_obj.customer, 'tax_id')

                sales_invoice_obj.shipping_address_name = sales_invoice_obj.customer_address

                self.get_sales_team(pos_profile_serie_obj.get('eico_sales_team'), sales_invoice_obj)

                if abs(sales_invoice_obj.get('discount_amount', 0)) > 0:
                    sales_invoice_obj.eico_discount_type = pos_profile_serie_obj.get('eico_discount_type')

                if sales_invoice_obj.is_return == 1:

                    sales_invoice_obj.eico_document_type = pos_profile_serie_obj.get('eico_document_type_cn')
                    sales_invoice_obj.eico_payment_type = pos_profile_serie_obj.get('eico_payment_type_nc')
                    sales_invoice_obj.eico_payment_term = pos_profile_serie_obj.get('eico_payment_term_nc')
                    sales_invoice_obj.eico_note_concept = pos_profile_serie_obj.get('eico_note_concept')
                    sales_invoice_obj.eico_description_note_concept = pos_profile_serie_obj.get('eico_description_note_concept')
                    sales_invoice_obj.eico_nvfac_obsb = pos_profile_serie_obj.get('eico_nvfac_obsb')

                    if not sales_invoice_obj.return_against:
                        sales_invoice_obj.eico_per_fini = getdate(self.posting_date)
                        sales_invoice_obj.eico_per_ffin = getdate(self.posting_date)

                else:
                    sales_invoice_obj.eico_document_type = pos_profile_serie_obj.get('eico_document_type')
                    sales_invoice_obj.eico_payment_type = pos_profile_serie_obj.get('eico_payment_type')
                    sales_invoice_obj.eico_payment_term = pos_profile_serie_obj.get('eico_payment_term')

            else:
                common_exception.value_required_exception(serie_field)
        else:
            common_exception.value_required_exception('pos_profile')

    def get_sales_team(self, eico_sales_team, sales_invoice_obj):

        sales_team = []

        for sales_team_row in eico_sales_team:
            sales_team.append(sales_team_row)

        sales_invoice_obj.set('sales_team', sales_team)

    def on_cancel(self):

        common_exception.validate_on_cancel()

    def on_trash(self):

        common_exception.validate_on_trash()

##

def is_pos_inv_merged(pos_inv_list, pos_closing_entry):
    # Se debe determinar las facturas agrupadas que ya estan validadas y sacarlas de data
    # No debe filtrar por status
    inv_list = [inv_ref.pos_invoice for inv_ref in pos_inv_list]
    sql_pos_inv = frappe.db.sql('''
        select pos_inv.name from `tabPOS Invoice Merge Log` as pos_merge
        inner join `tabPOS Invoice Reference` as pos_inv on pos_inv.parent = pos_merge.name
        where pos_merge.pos_closing_entry = %s
        and pos_inv.parenttype = 'POS Invoice Merge Log'
        and  pos_inv.parentfield = 'pos_invoices'
        and pos_inv.pos_invoice in %s
    ''', (pos_closing_entry, inv_list), as_dict=True)
    pos_inv = sql_pos_inv and True or False

    return pos_inv

def pos_eico_consolidate_pos_invoices(pos_invoices=None, closing_entry=None):

    invoices = pos_invoices or (closing_entry and closing_entry.get('pos_transactions')) or get_all_unconsolidated_invoices()
    invoice_by_customer = get_invoice_customer_map(invoices)

    if len(invoices) >= 10 and closing_entry:
        closing_entry.set_status(update=True, status='Queued')
        pos_eico_enqueue_job(pos_eico_create_merge_logs, invoice_by_customer=invoice_by_customer, closing_entry=closing_entry)
    else:
        pos_eico_create_merge_logs(invoice_by_customer, closing_entry)

def pos_eico_enqueue_job(job, **kwargs):

    check_scheduler_status()

    closing_entry = kwargs.get('closing_entry') or {}

    job_name = closing_entry.get("name")
    if not job_already_enqueued(job_name):
        enqueue(
            job,
            **kwargs,
            queue="long",
            timeout=10000,
            event="processing_merge_logs",
            job_name=job_name,
            now=frappe.conf.developer_mode or frappe.flags.in_test
        )

        if job == pos_eico_create_merge_logs:
            msg = _('POS Invoices will be consolidated in a background process')
        else:
            msg = _('POS Invoices will be unconsolidated in a background process')

        frappe.msgprint(msg, alert=1)

def pos_eico_create_merge_logs(invoice_by_customer, closing_entry=None):
        try:
            pos_closing_entry = closing_entry.get('name') if closing_entry else None
            is_created_pos_merge = False
            for customer, invoices in six.iteritems(invoice_by_customer):

                # Se mantiene para evitar duplicar las facturas creadas
                if is_pos_inv_merged(invoices, pos_closing_entry):
                    continue

                merge_log = frappe.new_doc('POS Invoice Merge Log')
                merge_log.posting_date = getdate(closing_entry.get('posting_date')) if closing_entry else nowdate()
                merge_log.customer = customer
                merge_log.pos_closing_entry = closing_entry.get('name') if closing_entry else None

                merge_log.set('pos_invoices', invoices)
                merge_log.save(ignore_permissions=True)

                # Se separa crear merge_log y submit
                merge_log.create_invoices()

                if not is_created_pos_merge:
                    is_created_pos_merge = True

            # Para garantizar que todos los POS Invoice Merge Log con sus Sales Invoice asociadas se mantengan
            if is_created_pos_merge:
                frappe.db.commit()

            # Consultar los merge_log creados a partir del closing_entry (Cuando no hay closing_entry se lanza error)
            if pos_closing_entry:
                # TODO: determinar filtro
                merge_log_list = frappe.db.get_values("POS Invoice Merge Log", filters={"pos_closing_entry": pos_closing_entry}, fieldname=["name"], order_by="creation")
                for row in merge_log_list:
                    merge_log_obj = frappe.get_doc("POS Invoice Merge Log", row[0])
                    merge_log_obj.submit_invoices()
                    merge_log_obj.submit()
            else:
                frappe.throw(_("Invalid Pos Closing Entry"))

            if closing_entry:
                closing_entry.set_status(update=True, status='Submitted')
                closing_entry.db_set('error_message', '')
                closing_entry.update_opening_entry()

        except Exception as e:
            frappe.db.rollback()
            message_log = frappe.message_log.pop() if frappe.message_log else str(e)
            error_message = safe_load_json(message_log)

            if closing_entry:
                closing_entry.set_status(update=True, status='Failed')
                closing_entry.db_set('error_message', error_message)
            raise

        finally:
            frappe.db.commit()
            frappe.publish_realtime('closing_process_complete', {'user': frappe.session.user})
