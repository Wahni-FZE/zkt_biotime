# Copyright (c) 2026, Wahni It Solutions UAE and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime, today

# BioTime punch_state: 0 Check In, 1 Check Out, 2 Break Out, 3 Break In, 4 Overtime In, 5 Overtime Out
LOG_TYPES = {"0": "IN", "3": "IN", "4": "IN", "1": "OUT", "2": "OUT", "5": "OUT"}


class BioTimeSettings(Document):
	pass


def get_transactions(settings, from_datetime, to_datetime):
	url = settings.server_url.strip().rstrip("/")

	login = requests.post(
		f"{url}/jwt-api-token-auth/",
		json={"username": settings.username, "password": settings.get_password("password")},
		timeout=60,
	)
	if not login.ok:
		frappe.throw(_("BioTime login failed. Please check Server URL, Username and Password."))
	headers = {"Authorization": f"JWT {login.json()['token']}"}

	transactions = []
	page = 1
	while True:
		response = requests.get(
			f"{url}/iclock/api/transactions/",
			headers=headers,
			params={
				"start_time": get_datetime(from_datetime).strftime("%Y-%m-%d %H:%M:%S"),
				"end_time": get_datetime(to_datetime).strftime("%Y-%m-%d %H:%M:%S"),
				"page": page,
				"page_size": 500,
			},
			timeout=60,
		)
		response.raise_for_status()
		data = response.json()
		transactions += data.get("data") or []

		if not data.get("next"):
			break
		page += 1

	return transactions


def sync_checkins(from_datetime, to_datetime):
	"""Create Employee Checkins for BioTime transactions between the given datetimes."""
	settings = frappe.get_single("BioTime Settings")
	transactions = get_transactions(settings, from_datetime, to_datetime)
	created = 0
	failed = 0

	for row in transactions:
		transaction_id = str(row["id"])

		# already fetched
		if frappe.db.exists("Employee Checkin", {"biotime_transaction_id": transaction_id}):
			continue

		employee = frappe.db.get_value("Employee", {"attendance_device_id": str(row["emp_code"])}, "name")
		if not employee:
			continue

		try:
			frappe.get_doc(
				{
					"doctype": "Employee Checkin",
					"employee": employee,
					"time": row["punch_time"],
					"log_type": LOG_TYPES.get(str(row.get("punch_state"))),
					"device_id": row.get("terminal_alias") or row.get("terminal_sn"),
					"biotime_transaction_id": transaction_id,
				}
			).insert(ignore_permissions=True)
			created += 1
		except Exception:
			failed += 1
			frappe.clear_messages()
			frappe.log_error(f"BioTime Checkin Failed: Transaction {transaction_id}")

	message = _("Fetched {0} transaction(s) from BioTime. Created {1} new checkin(s).").format(
		len(transactions), created
	)
	if failed:
		message += " " + _("Failed {0}, please check Error Log.").format(failed)
	return message


def sync_from_last_sync_time():
	settings = frappe.get_single("BioTime Settings")
	now = now_datetime()

	# go back 1 hour to catch punches uploaded late by the device
	from_datetime = add_to_date(settings.last_sync_time, hours=-1) if settings.last_sync_time else today()

	message = sync_checkins(from_datetime, now)
	frappe.db.set_single_value("BioTime Settings", "last_sync_time", now)
	return message


def scheduled_sync():
	if frappe.db.get_single_value("BioTime Settings", "enabled"):
		sync_from_last_sync_time()


@frappe.whitelist()
def sync_now():
	frappe.only_for(["System Manager", "HR Manager"])
	return sync_from_last_sync_time()


@frappe.whitelist()
def fetch_transactions(from_date, to_date):
	frappe.only_for(["System Manager", "HR Manager"])
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	return sync_checkins(f"{from_date} 00:00:00", f"{to_date} 23:59:59")
