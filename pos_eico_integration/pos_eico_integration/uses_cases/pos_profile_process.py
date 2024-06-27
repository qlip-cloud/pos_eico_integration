# -*- coding: utf-8 -*-
# Copyright (c) 2024, Aryrosa Fuentes and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist()
def get_naming_series():
	return frappe.get_meta("Sales Invoice").get_field("naming_series").options
