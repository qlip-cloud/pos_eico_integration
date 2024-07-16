from frappe import _, throw

def value_required_exception(title):

	throw(_("The value {0} is required").format(title))

def validate_on_cancel():

	throw(_("It is not allowed to cancel the document"))

def validate_on_trash():

	throw(_("It is not allowed to delete the document"))
