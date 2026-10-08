To add a contact form that creates CRM requests:

1.  Edit a website page and drop a **Form** block.
2.  In the form options, set **Action** to **CRM request**.
3.  Keep the required fields (subject, e-mail and message) and add the phone
    number if needed.

Submitted forms appear in the CRM requests.

To link each request to a new contact when the address is unknown, the form
must also send these parameters (they are read from the request, not saved on
the CRM request):

- `firstname` and `lastname`;
- `title` (optional): the shortcut of a contact title, for example one of
  the titles shown on public forms.

Without a first or last name, requests from unknown addresses stay
unassigned. The *Contact us* page of `my_compassion` is an example of such a
form.
