// Copyright (c) 2026, Wahni It Solutions UAE and contributors
// For license information, please see license.txt

frappe.ui.form.on("BioTime Settings", {
	sync_now(frm) {
		run_biotime_sync(frm, "sync_now");
	},

	fetch_transactions(frm) {
		if (!frm.doc.from_date || !frm.doc.to_date) {
			frappe.throw(__("Please set From Date and To Date"));
		}
		run_biotime_sync(frm, "fetch_transactions", {
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date,
		});
	},
});

function run_biotime_sync(frm, method, args) {
	const save = frm.is_dirty() ? frm.save() : Promise.resolve();

	save.then(() => {
		frappe.call({
			method: "zkt_biotime.zkt_biotime.doctype.biotime_settings.biotime_settings." + method,
			args: args,
			freeze: true,
			freeze_message: __("Syncing with BioTime..."),
			callback(r) {
				frappe.msgprint(r.message);
				frm.reload_doc();
			},
		});
	});
}
