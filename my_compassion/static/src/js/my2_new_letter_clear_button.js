/** @odoo-module **/

/*
 * Clear-letter button for the new-letter form.
 *
 * Used in /templates/pages/my2_new_letter.xml
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";
import {_t} from "@web/core/l10n/translation";
import {letterAttachments} from "@my_compassion/js/my2_letter_attachments";

publicWidget.registry.ClearLetterButtonWidget = publicWidget.Widget.extend({
  selector: "#new_letter_form",
  // Binds events to methods within the widget
  events: {
    "input #letter-input": "_onUserInput",
    "click #clear-letter-button-container": "_onClearClick",
    "click .template-image": "_onUserInput",
    "change #letter-attachments": "_onUserInput",
  },

  /**
   * The start method is part of the widget's lifecycle.
   * It runs once the widget is attached to the DOM.
   */
  start: function () {
    this._super.apply(this, arguments);
    // Run an initial check in case a draft is loaded with pre-existing text
    this._toggleClearButton();
  },

  /**
   * Called when the user writes, adds/remove an image, selects a template.
   * @private
   */
  _onUserInput: function () {
    this._toggleClearButton();
  },

  /**
   * Called when the "Clear letter" button is clicked.
   * @private
   */
  _onClearClick: function (ev) {
    ev.preventDefault();
    // Remove all written text from the textarea
    this.$("#letter-input").val("");

    //Remove the uploaded files from the input
    const fileInput = this.$("#letter-attachments")[0];
    fileInput.value = "";
    letterAttachments.files = [];
    //Clear the uploaded images container
    this.$("#uploaded-files-container").empty();

    // Remove the selected template image
    this.$("#selected-template").remove();

    // Restore the select template button label to default
    const buttonLabel = this.$("#template-selection-label");
    if (buttonLabel.length) {
      buttonLabel.text(_t("Select a template"));
    }
    /*
        BACKEND SYNCING
        */
    // Unlink the draft generator from the user
    const childId = this.$("#child-dropdown").val();
    rpc("/my2/letter/unlink_draft_generator", {
      child_id: parseInt(childId, 10),
    }).catch((error) => {
      console.error("Error unlinking draft generator:", error);
    });
    //Clear the generator_id value got from the previously loaded draft if any.
    this.$("input[name='generator_id']").val("");

    this._toggleClearButton();
  },

  /**
   * The core logic to show or hide the button based on the form content.
   * @private
   */
  _toggleClearButton: function () {
    const hasText = this.$("#letter-input").val().trim().length > 0;
    const selectedTemplate = this.$("#selected-template").length > 0;
    const hasAttachments = this.$("#letter-attachments")[0].files.length > 0;

    this.$("#clear-letter-button-container").toggle(
      hasText || selectedTemplate || hasAttachments
    );
  },
});
