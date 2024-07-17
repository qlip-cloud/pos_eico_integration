frappe.ui.form.on('POS Closing Entry', {
	
	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status == 'Failed') {
			frm.add_custom_button(__('Retry'), function () {
				$(`button[data-label='${__("Retry")}']`).attr('disabled', true);
				frm.call('retry', {}, () => {
					frm.reload_doc();
				});
			});
		}
	}

})
