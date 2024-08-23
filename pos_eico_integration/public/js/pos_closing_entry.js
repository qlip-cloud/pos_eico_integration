frappe.ui.form.on('POS Closing Entry', {

	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status == 'Failed') {
			frm.add_custom_button(__('Retry'), function () {
				try {
					$(`button[data-label='${__("Retry")}']`).attr('disabled', true);
					frm.call('retry', {}, (r) => {
						frm.reload_doc();
					});
				} catch (error) {
					frm.reload_doc();
				}
			});
		}
	}

})