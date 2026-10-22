Glue between MyCompassion and the PayU GPO payment provider, installed
automatically with both.

A card a sponsor saves with PayU that becomes the card of contract groups
(first payment of a digital sponsorship, or the update-card page) pays the
monthly contributions: it is registered at PayU as a recurring card
(`recurring: FIRST`, then `STANDARD`). Other saved cards stay cards on file.

A payer known by email only (fast checkout, visitor donation) has a
placeholder name: no name is sent to PayU for them, and the name typed on
the card (or PayU's buyer) replaces the placeholder once the payment is done.

A monthly charge PayU refuses (it cancels the order of the charge) reaches
the contracts' dunning (`_on_digital_charge_failed`) once, when its
notification or status read moves the charge to error. Repeated
notifications start nothing, nor does a notification that does not match
the charge (the PayU module keeps it pending, for staff), nor a charge PayU
cancelled because nobody captured it (automatic collection off on the point
of sale): the card works. A dunning that fails is logged for staff and never
undoes the refusal.

A payment PayU never confirmed is no certain refusal: my_compassion then
does not give the basket back to be paid again, as the payment may have
been made.

A MyCompassion order takes one card payment at a time. Before PayU's card
route sends a card, my_compassion refuses it while another payment of the
order may still succeed (two payment forms may each have made a draft);
the route then cancels the draft and shows the reason.

This module comes with changes in my_compassion, for every provider:

- the update-card page pays arrears with the new card, which then replaces
  the group's card;
- with nothing due, the page saves a card without a payment only with a
  provider that can (PayU cannot), and otherwise says so;
- a group takes a card only of its sponsor, in its company and at its
  payment mode's provider;
- an off-session charge decides on what its own send returned, not on a
  state a provider notification set since.
