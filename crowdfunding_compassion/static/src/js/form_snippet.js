odoo.define("crowdfunding_compassion.form_snippet", function (require) {
  "use strict";

  var core = require("web.core");
  var FormEditorRegistry = require("website_form.form_editor_registry");

  var _t = core._t;

  FormEditorRegistry.add("crowdfunding_project_step1", {
    formFields: [
      {
        type: "char",
        modelRequired: true,
        name: "name",
        string: _t("Name of your project"),
        placeholder: _t("Use a catchy name that is accurate to your idea."),
      },
      {
        type: "text",
        modelRequired: true,
        name: "description",
        string: _t("Project description"),
        placeholder: _t(
          "Aim of the project, why you want to create it, for which " +
            "purpose and any useful information that the donors should know."
        ),
      },
      {
        type: "date",
        modelRequired: true,
        name: "deadline",
        string: _t("Deadline of project"),
        placeholder: _t("Indicate when your project should end."),
      },
      {
        type: "binary",
        modelRequired: false,
        name: "cover_photo",
        string: _t("Cover Photo"),
        placeholder: _t(
          "Upload a cover photo that represents your project. " +
            "Best size: 900x400px"
        ),
      },
      {
        type: "url",
        modelRequired: false,
        name: "presentation_video",
        string: _t("Presentation Video"),
        placeholder: _t(
          "Paste any video link that showcase your project " +
            "(e.g. https://vimeo.com/jlkj34ek5)"
        ),
      },
      {
        type: "selection",
        modelRequired: true,
        name: "type",
        string: _t("My project is"),
        selection: [
          ["individual", _t("Individual")],
          ["collective", _t("Collective")],
        ],
      },
      {
        type: "url",
        modelRequired: false,
        name: "facebook_url",
        string: _t("Facebook link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "twitter_url",
        string: _t("Twitter link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "instagram_url",
        string: _t("Instagram link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "personal_web_page_url",
        string: _t("Personal web page"),
      },
    ],
  });

  FormEditorRegistry.add("crowdfunding_project_step2", {
    formFields: [
      {
        type: "integer",
        name: "number_sponsorships_goal",
        string: _t("Sponsor children"),
        placeholder: _t(
          "If you want to propose people to sponsor a child, " +
            "please indicate the goal number."
        ),
      },
      {
        type: "integer",
        name: "number_csp_goal",
        string: _t("Sponsor mums and babies"),
        placeholder: _t(
          "If you want to propose people to sponsor a mum and her baby, " +
            "please indicate the goal number."
        ),
      },
      {
        type: "integer",
        name: "product_number_goal",
        string: _t("Product goal"),
        placeholder: _t("Indicate your goal here."),
      },
      {
        type: "many2one",
        name: "product_id",
        relation: "product.product",
        string: _t("Product"),
        placeholder: _t("Select a fund to support."),
        domain: [["activate_for_crowdfunding", "=", true]],
      },
      {
        type: "integer",
        name: "project_id",
        string: _t("Project"),
      },
    ],
  });

  FormEditorRegistry.add("crowdfunding_project_step3", {
    formFields: [
      {
        type: "many2one",
        modelRequired: true,
        name: "partner_title",
        string: _t("Title"),
        relation: "res.partner.title",
        domain: [["website_published", "=", true]],
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_firstname",
        string: _t("Firstname"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_lastname",
        string: _t("Lastname"),
      },
      {
        type: "char",
        modelRequired: false,
        name: "nickname",
        string: _t("Name of your group / organisation"),
      },
      {
        type: "email",
        modelRequired: true,
        name: "partner_email",
        string: _t("Email"),
      },
      {
        type: "date",
        modelRequired: false,
        name: "partner_birthdate_date",
        string: _t("Birthdate"),
      },
      {
        type: "tel",
        modelRequired: false,
        name: "partner_phone",
        string: _t("Phone"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_street",
        string: _t("Street"),
      },
      {
        type: "integer",
        modelRequired: true,
        name: "partner_zip",
        string: _t("Postal code"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_city",
        string: _t("City"),
      },
      {
        type: "binary",
        modelRequired: false,
        name: "profile_picture",
        string: _t("Profile picture"),
      },
      {
        type: "text",
        modelRequired: true,
        name: "personal_motivation",
        string: _t("Personal motivation"),
      },
    ],
  });

  FormEditorRegistry.add("crowdfunding_project_update", {
    formFields: [
      {
        type: "char",
        modelRequired: true,
        name: "name",
        string: _t("Name of your project"),
        placeholder: _t("Use a catchy name that is accurate to your idea."),
      },
      {
        type: "text",
        modelRequired: true,
        name: "description",
        string: _t("Project description"),
        placeholder: _t(
          "Aim of the project, why you want to create it, for which " +
            "purpose and any useful information that the donors should know."
        ),
      },
      {
        type: "date",
        modelRequired: true,
        name: "deadline",
        string: _t("Deadline of project"),
        placeholder: _t("Indicate when your project should end."),
      },
      {
        type: "binary",
        modelRequired: false,
        name: "cover_photo",
        string: _t("Cover Photo"),
        placeholder: _t(
          "Upload a cover photo that represents your project. " +
            "Best size: 900x400px"
        ),
      },
      {
        type: "url",
        modelRequired: false,
        name: "presentation_video",
        string: _t("Presentation Video"),
        placeholder: _t(
          "Paste any video link that showcase your project " +
            "(e.g. https://vimeo.com/jlkj34ek5)"
        ),
      },
      {
        type: "selection",
        modelRequired: true,
        name: "type",
        string: _t("My project is"),
        selection: [
          ["individual", _t("Individual")],
          ["collective", _t("Collective")],
        ],
      },
      {
        type: "url",
        modelRequired: false,
        name: "facebook_url",
        string: _t("Facebook link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "twitter_url",
        string: _t("Twitter link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "instagram_url",
        string: _t("Instagram link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "personal_web_page_url",
        string: _t("Personal web page"),
      },
      {
        type: "many2one",
        name: "project_id",
        relation: "crowdfunding.project",
        string: _t("Project to update"),
      },
    ],
  });

  FormEditorRegistry.add("crowdfunding_participant_update", {
    formFields: [
      {
        type: "char",
        modelRequired: false,
        name: "nickname",
        string: _t("Name of your group / organisation"),
      },
      {
        type: "binary",
        modelRequired: false,
        name: "profile_picture",
        string: _t("Profile picture"),
      },
      {
        type: "text",
        modelRequired: true,
        name: "personal_motivation",
        string: _t("Personal motivation"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "facebook_url",
        string: _t("Facebook link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "twitter_url",
        string: _t("Twitter link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "instagram_url",
        string: _t("Instagram link"),
      },
      {
        type: "url",
        modelRequired: false,
        name: "personal_web_page_url",
        string: _t("Personal web page"),
      },
      {
        type: "many2one",
        name: "participant_id",
        relation: "crowdfunding.participant",
        string: _t("Participant to update"),
      },
    ],
  });
});
