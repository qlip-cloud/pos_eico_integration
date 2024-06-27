// Copyright (c) 2024, Aryrosa Fuentes and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Profile', {
	setup: function(frm) {
		frm.set_query("eico_document_type", function() {
			return {
				filters:{
					'dt_name': 'Sales Invoice'
				}
			}
		});
		frm.set_query("eico_document_type_nc", function() {
			return {
				filters:{
					'dt_name': 'Sales Invoice'
				}
			}
		});
		frm.set_query("eico_note_concept", function() {
			return {
				filters:{
					'dt_name': 'Sales Invoice'
				}
			}
		});
		frm.set_query("eico_discount_type", function() {
			return {
				filters:{
					'dt_name': 'Sales Invoice'
				}
			}
		});
	},
	refresh: function(frm) {
		frappe.call({
			type: "GET",
			method: "pos_eico_integration.pos_eico_integration.uses_cases.pos_profile_process.get_naming_series",
			callback: function(r){
				if(r.message){
					frm.set_df_property("eico_series", "options", r.message.split("\n"));
					frm.refresh_field("eico_series");
					frm.set_df_property("eico_series_credit_note", "options", r.message.split("\n"));
					frm.refresh_field("eico_series_credit_note");
				}
			}
		});
	}
});
