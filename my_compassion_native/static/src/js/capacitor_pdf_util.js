/** @odoo-module **/

/**
 * Downloads a document and opens it through the native Capacitor viewer.
 * The inline PDF viewer renders badly in the app WebView, so native_pdf_intercept
 * routes in-app PDF links here to hand the file to the OS viewer instead.
 */
export async function downloadAndOpenPDF(url, filename) {
  try {
    if (window.$ && window.$.blockUI) {
      window.$.blockUI({message: "Opening Document..."});
    }

    const response = await fetch(url, {method: "GET"});
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    const blob = await response.blob();
    const reader = new FileReader();

    reader.readAsDataURL(blob);
    reader.onloadend = async () => {
      try {
        const base64data = reader.result.split(",")[1];

        const Filesystem = window.Capacitor.Plugins.Filesystem;
        const savedFile = await Filesystem.writeFile({
          path: filename,
          data: base64data,
          directory: "CACHE",
        });

        const FileOpener = window.Capacitor.Plugins.FileOpener;
        if (FileOpener) {
          await FileOpener.open({
            filePath: savedFile.uri,
            contentType: "application/pdf",
          });
        }
      } catch (error) {
        console.error("Capacitor PDF: Error opening document", error);
        alert("Could not load the document. Please try again.");
      } finally {
        if (window.$ && window.$.unblockUI) {
          window.$.unblockUI();
        }
      }
    };
  } catch (error) {
    console.error("Capacitor PDF: Error downloading document", error);
    if (window.$ && window.$.unblockUI) {
      window.$.unblockUI();
    }
    alert("Could not load the document. Please try again.");
  }
}
