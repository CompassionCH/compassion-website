/**
 * Handles the uploaded attachments from the user when filling the new letter form
 *
 * Used in /templates/pages/my2_new_letter.xml
 */
document.addEventListener('DOMContentLoaded', () => {

    // Get references to the file input and the container for uploaded files
    const fileInput = document.getElementById('letter-attachments');
    const container = document.getElementById('uploaded-files-container');

    let uploadedFiles = [];

    /**
     * Helper function to generate a unique key for each file
     * This ensures we can track files even if they have the same name
     */
    const generateFileKey = file =>
        `${file.name}-${file.size}-${file.type}-${file.lastModified}`;

    /**
     * Updates the file input with the current list of uploaded files.
     *
     * The `files` property of a file input is a read-only FileList
     * To work around this limitation, we use a DataTransfer object to create a new FileList:
     *
     * This ensures that the file input always reflects the current state of the `uploadedFiles` array,
     * even after files are added or removed.
     */
    const updateFileInput = () => {
        const dataTransfer = new DataTransfer();
        uploadedFiles.forEach(file => dataTransfer.items.add(file));
        fileInput.files = dataTransfer.files;
    };

    // Function to create a DOM element for a file attachment
    const createFileElement = (file, dataUrl) => {
        const fileDiv = document.createElement('div');
        fileDiv.className = 'col-4 uploaded-file position-relative';

        // Store the file's unique key as a data attribute for further management
        fileDiv.dataset.fileKey = generateFileKey(file);

        // Create an img element that renders the file image
        // TODO we should force only images, compress them, on convert them to .jpeg
        const preview = Object.assign(document.createElement('img'), {
            className: 'img-fluid',
            src: dataUrl
        });

        // Create a paragraph element to display the file name
        const fileName = Object.assign(document.createElement('p'), {
            textContent: file.name
        });

        // Create a remove button
        const removeBtn = Object.assign(document.createElement('button'), {
            className: 'btn btn-danger remove-attachment-button',
            innerHTML: 'X'
        });

        fileDiv.append(preview, fileName, removeBtn);
        return fileDiv;
    };

    // Event delegation for remove buttons
    // Instead of adding a listener to each button, we add one listener to the container
    container.addEventListener('click', e => {
        if (e.target.classList.contains('remove-attachment-button')) {
            // Find the closest file container
            const fileDiv = e.target.closest('.uploaded-file');
            if (!fileDiv) return;

            const fileKey = fileDiv.dataset.fileKey;

            // Remove the file from the uploadedFiles array
            uploadedFiles = uploadedFiles.filter(f => generateFileKey(f) !== fileKey);

            // Remove the file container from the DOM
            fileDiv.remove();

            // Update the file input to reflect the changes
            updateFileInput();
        }
    });

    // Event listener for file input changes
    fileInput.addEventListener('change', () => {
        // Convert the FileList to an array
        const newFiles = Array.from(fileInput.files);

        // Create a Set of existing file keys for quick lookup
        const existingKeys = new Set(uploadedFiles.map(generateFileKey));

        // Process each new file
        newFiles.forEach(file => {
            const fileKey = generateFileKey(file);

            // Skip if the file is already in the list
            if (existingKeys.has(fileKey)) return;

            // Add the file to the list of uploaded files
            existingKeys.add(fileKey);
            uploadedFiles.push(file);

            // Use FileReader to read the file as a data URL (for showing the image of the file)
            const reader = new FileReader();
            reader.onload = e => {

                // Check if the file is still in the uploadedFiles array
                if (!uploadedFiles.some(f => generateFileKey(f) === fileKey)) return;

                // Create and append the file element to the container
                container.appendChild(createFileElement(file, e.target.result));
            };
            reader.onerror = () => {
                // Handle file read errors
                uploadedFiles = uploadedFiles.filter(f => generateFileKey(f) !== fileKey);
                updateFileInput();
                alert(`Error reading ${file.name}`);
            };
            // Start reading the file
            reader.readAsDataURL(file);
        });
        // Update the file input to reflect the new files
        updateFileInput();
    });
});

