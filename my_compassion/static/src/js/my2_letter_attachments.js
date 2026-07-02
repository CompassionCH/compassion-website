/** @odoo-module **/

/**
 * Pending client-side attachments for the new-letter form. The add-a-picture
 * input fills `files`; the clear button and the submit handler reset it. A
 * single exported container is the shared reference between those modules:
 * `.files` is reassigned in place so every importer sees the current array.
 */
export const letterAttachments = {files: []};
