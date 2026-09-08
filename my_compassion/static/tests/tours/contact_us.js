import {animationFrame, click} from "@odoo/hoot-dom";
import {registry} from "@web/core/registry";
import {stepUtils} from "@web_tour/tour_service/tour_utils";

const TOKEN_KEY = "my_compassion.contact_us_tour_token";
const fromUrl = new URLSearchParams(location.search).get("tour_token");
if (fromUrl) {
  sessionStorage.setItem(TOKEN_KEY, fromUrl);
}
const token = sessionStorage.getItem(TOKEN_KEY) || "";

const KNOWN = {
  firstname: "Camille",
  lastname: "Rochat",
  phone: "0041216541288",
  email: `camille.rochat+${token}@example.org`,
  subject: `Change of payment date - ${token}`,
  message: "I would like to change the date my monthly payment is taken.",
};

const UNKNOWN = {
  firstname: "Lukas",
  lastname: "Baumann",
  phone: "0041313017654",
  email: `lukas.baumann+${token}@example.org`,
  subject: `Sponsoring a child - ${token}`,
  message: "I would like to sponsor a child and do not know where to start.",
};

const sendMessage = (contact) => [
  {
    content: "Choose a title",
    trigger: "#contactus_form select[name=title]",
    run: "selectByIndex 1",
  },
  {
    content: "Fill in the first name",
    trigger: "#contactus_form_firstname",
    run: `edit ${contact.firstname}`,
  },
  {
    content: "Fill in the last name",
    trigger: "#contactus_form_lastname",
    run: `edit ${contact.lastname}`,
  },
  {
    content: "Fill in the phone number",
    trigger: "#contactus_form_phone_number",
    run: `edit ${contact.phone}`,
  },
  {
    content: "Fill in the e-mail address",
    trigger: "#contactus_form_email",
    run: `edit ${contact.email}`,
  },
  {
    content: "Fill in the subject of the message",
    trigger: "#contactus_subject",
    run: `edit ${contact.subject}`,
  },
  {
    content: "Write the message",
    trigger: "#contactus_message",
    run: `edit ${contact.message}`,
  },
  {
    content: "Send the message",
    trigger: "#contactus_form .s_website_form_send",
    run: "click",
    expectUnloadPage: true,
  },
  {
    content: "The message went through",
    trigger: "h5:contains('Your message has been sent successfully')",
  },
];

registry.category("web_tour.tours").add("contact_us", {
  url: "/contactus",
  steps: () => [
    {
      content: "The MyCompassion contact form is displayed",
      trigger: "#contactus_form_top form#contactus_form select[name=title]",
    },
    ...sendMessage(KNOWN),
    stepUtils.goToUrl("/contactus"),
    ...sendMessage(UNKNOWN),
    stepUtils.goToUrl("/odoo"),
    ...stepUtils.goToAppSteps("crm_request.support_root", "Open the Support app"),
    {
      content: "Drop the default filters, so that every request is listed",
      trigger: ".o_control_panel .o_searchview",
      async run() {
        let facet = document.querySelector(".o_searchview_facet .o_facet_remove");
        while (facet) {
          await click(facet, {interactive: false});
          await animationFrame();
          facet = document.querySelector(".o_searchview_facet .o_facet_remove");
        }
      },
    },
    {
      content: "No search filter is left",
      trigger: ".o_searchview:not(:has(.o_searchview_facet))",
    },
    {
      content: "The message of the known contact reached the Support",
      trigger: `.o_kanban_record:contains("${KNOWN.subject}")`,
    },
    {
      content: "Open the request of the contact Odoo did not know",
      trigger: `.o_kanban_record:contains("${UNKNOWN.subject}") h4 a`,
      run: "click",
    },
    {
      content: "The request carries the message that was written",
      trigger: `.o_form_view [name=description] textarea:value("${UNKNOWN.message}")`,
    },
    {
      content: "Focus the contact of the request",
      trigger: ".o_form_view [name=partner_id] input",
      run: "click",
    },
    {
      content: "Open the contact the request is associated with",
      trigger: ".o_form_view [name=partner_id] button.o_external_button",
      run: "click",
    },
    {
      content: "The contact holds the name that was filled in the form",
      trigger:
        `.o_form_view [name=lastname]:visible ` + `input:value("${UNKNOWN.lastname}")`,
    },
    {
      content: "The contact holds the e-mail address that was filled in the form",
      trigger: `.o_form_view [name=email] input:value("${UNKNOWN.email}")`,
    },
  ],
});
