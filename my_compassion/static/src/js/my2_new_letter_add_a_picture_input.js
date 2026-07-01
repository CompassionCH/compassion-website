/** @odoo-module **/

/**
 * Handles the uploaded attachments files from the user when filling the new letter form
 *
 * Used in /templates/pages/my2_new_letter.xml
 */

import {whenReady} from "@odoo/owl";
import {letterAttachments} from "@my_compassion/js/my2_letter_attachments";

whenReady(() => {
  // Constants
  const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
  const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
  const COMPRESSION_QUALITY = 0.9; // 90%
  const MAX_DIMENSION = 800; // 800px width/height

  // Retrieve the input where the users put files and the container for displaying the file preview
  const fileInput = document.getElementById("letter-attachments");
  const container = document.getElementById("uploaded-files-container");
  if (!fileInput || !container) {
    return;
  }

  /**
   * Generates a unique key for a file based on its metadata.
   *
   * @param {File} file - The file to generate a key for.
   * @returns {string} A unique key combining the file's name, size, type, and last modified date.
   */
  const generateFileKey = (file) =>
    `${file.name}-${file.size}-${file.type}-${file.lastModified}`;

  /**
   * Updates the file input element with the current list of uploaded files.
   * Uses a DataTransfer object to work around the read-only nature of the FileList.
   */
  const updateFileInput = () => {
    const dataTransfer = new DataTransfer();
    letterAttachments.files.forEach((file) => dataTransfer.items.add(file));
    fileInput.files = dataTransfer.files;
  };

  /**
   * Reads a file as a Data URL (base64 encoded string).
   *
   * @param {File} file - The file to read.
   * @returns {Promise<string>} A promise that resolves with the file's Data URL.
   */
  const readFileAsDataURL = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  /**
   * Compresses and converts an image file to JPEG format.
   * Resizes the image to a maximum dimension and sets the quality based on
   * MAX_DIMENSION and MAX_QUALITY constants.
   *
   * @param {File} originalFile - The image file to compress.
   * @returns {Promise<File>} A promise that resolves with the compressed JPEG file.
   */
  const compressImage = (originalFile) =>
    new Promise((resolve, reject) => {
      const img = new Image();
      img.src = URL.createObjectURL(originalFile);

      img.onload = () => {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        // Calculate new dimensions
        let width = img.width;
        let height = img.height;

        // Resize the image proportionally to fit MAX_DIMENSION if needed
        if (width > height && width > MAX_DIMENSION) {
          height *= MAX_DIMENSION / width;
          width = MAX_DIMENSION;
        } else if (height > MAX_DIMENSION) {
          width *= MAX_DIMENSION / height;
          height = MAX_DIMENSION;
        }

        // Set canvas dimensions
        canvas.width = width;
        canvas.height = height;

        // Draw and compress image
        ctx.drawImage(img, 0, 0, width, height);

        // Convert the canvas element to a Blob with a MIME type of image/jpeg
        canvas.toBlob(
          (blob) => {
            if (!blob) return reject(new Error("Image compression failed"));

            // Create new File object with JPEG format
            const compressedFile = new File(
              [blob],
              originalFile.name.replace(/\.[^/.]+$/, ".jpg"),
              {
                type: "image/jpeg",
              }
            );

            URL.revokeObjectURL(img.src);
            resolve(compressedFile);
          },
          "image/jpeg",
          COMPRESSION_QUALITY
        );
      };

      img.onerror = reject;
    });

  /**
   * Creates a DOM element to display an uploaded file.
   * Includes a preview image, file name, and a remove button.
   *
   * @param {File} file - The file to create an element for.
   * @param {string} dataUrl - The Data URL of the file for the preview.
   * @returns {HTMLElement} The created file container element.
   */
  const createFileElement = (file, dataUrl) => {
    const fileDiv = document.createElement("div");
    fileDiv.className = "col-4 uploaded-file position-relative";
    fileDiv.dataset.fileKey = generateFileKey(file);

    const preview = Object.assign(document.createElement("img"), {
      className: "img-fluid",
      src: dataUrl,
      style: "max-height: 200px; object-fit: contain;",
    });

    const fileName = Object.assign(document.createElement("p"), {
      textContent: file.name,
    });

    const removeBtn = Object.assign(document.createElement("button"), {
      className: "btn btn-danger remove-attachment-button text-center",
      innerHTML: "×",
    });

    fileDiv.append(preview, fileName, removeBtn);
    return fileDiv;
  };

  /**
   * Handles click events on the uploaded files container.
   * Removes a file when its "X" button is clicked.
   */
  container.addEventListener("click", (e) => {
    if (e.target.classList.contains("remove-attachment-button")) {
      const fileDiv = e.target.closest(".uploaded-file");
      if (!fileDiv) return;

      const fileKey = fileDiv.dataset.fileKey;
      letterAttachments.files = letterAttachments.files.filter(
        (f) => generateFileKey(f) !== fileKey
      );
      fileDiv.remove();
      updateFileInput();
    }
  });

  /**
   * Handles file input change events.
   * Validates, compresses, and processes newly uploaded files.
   * Displays previews and updates the file input with the current list of files.
   */
  fileInput.addEventListener("change", async () => {
    const newFiles = Array.from(fileInput.files);
    const existingKeys = new Set(letterAttachments.files.map(generateFileKey));

    try {
      for (const file of newFiles) {
        // Validate file type
        if (!ACCEPTED_TYPES.includes(file.type)) {
          alert(`Unsupported file type: ${file.type}. Please upload an image.`);
          continue;
        }

        // Validate file size
        if (file.size > MAX_FILE_SIZE) {
          alert(`File ${file.name} is too large (max ${MAX_FILE_SIZE}MB)`);
          continue;
        }

        const fileKey = generateFileKey(file);
        if (existingKeys.has(fileKey)) continue;

        try {
          // Compress and convert to JPEG
          const compressedFile = await compressImage(file);
          const compressedKey = generateFileKey(compressedFile);

          if (existingKeys.has(compressedKey)) continue;

          // Read compressed file for preview
          const dataUrl = await readFileAsDataURL(compressedFile);

          // Update collections
          existingKeys.add(compressedKey);
          letterAttachments.files.push(compressedFile);

          // Create and append preview
          container.appendChild(createFileElement(compressedFile, dataUrl));
        } catch (error) {
          console.error("Error processing file:", error);
          alert(`Failed to process ${file.name}: ${error.message}`);
          letterAttachments.files = letterAttachments.files.filter(
            (f) => generateFileKey(f) !== fileKey
          );
        }
      }
    } finally {
      updateFileInput();
    }
  });
});
