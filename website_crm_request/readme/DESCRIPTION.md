This module lets website forms create CRM requests (`crm.claim`, from
`crm_request`). Messages sent from a contact form arrive in the same request
queue as the ones received by e-mail.

It adds **CRM request** as an action in the website form builder, with the
fields a visitor can fill in: subject, e-mail, phone number and message.

Each request is linked to the contact who sent it, as the mail gateway does
for e-mails:

- if a contact already has the e-mail address, the request is assigned to that
  contact and uses their language, so the Reply button works;
- otherwise, if the form also sends a first name or a last name, a new contact
  is created from the form data (name, e-mail, phone and title);
- if the form sends neither, the request stays unassigned: an unassigned
  request is better than a contact without a name.

The address is matched even when it belongs to Compassion. `crm_request`
excludes those addresses on incoming e-mails because they usually mean a
forwarded message, but on a form the visitor typed the address themselves.
