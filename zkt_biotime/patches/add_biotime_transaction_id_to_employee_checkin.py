from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee Checkin": [
				{
					"fieldname": "biotime_transaction_id",
					"label": "BioTime Transaction ID",
					"fieldtype": "Data",
					"insert_after": "device_id",
					"read_only": 1,
					"no_copy": 1,
					"unique": 1,
					"description": "Set when the checkin is fetched from BioTime; used to skip already fetched entries.",
				}
			]
		},
		update=True,
	)
