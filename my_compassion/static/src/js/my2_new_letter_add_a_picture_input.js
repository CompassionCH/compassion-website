/**
 * Handles the uploaded attachments from the user when filling the new letter form
 *
 * Is used in /templates/pages/my2_new_letter.xml
 */
document.getElementById('letter-attachments').addEventListener('change', function(event) {
    const files = Array.from(event.target.files); // Convert FileList to Array
    const container = document.getElementById('uploaded-files-container');

    // Initialize uploadedFiles array if not already defined
    if (!window.uploadedFiles) {
        window.uploadedFiles = [];
    }

    files.forEach((file, index) => {
        const fileReader = new FileReader();

        fileReader.onload = function(e) {
            // Create a new div element to hold the file information
            const fileDiv = document.createElement('div');
            // Add Bootstrap classes for layout and custom class for styling
            fileDiv.classList.add('col-4', 'uploaded-file', 'position-relative');

            // Create an img element to display the file as an image
            const img = document.createElement('img');
            img.src = e.target.result;
            img.classList.add('img-fluid');

            // Create a p element to display the file name
            const fileName = document.createElement('p');
            fileName.textContent = file.name;

            // Create a button element for the "X" to remove the file
            const removeButton = document.createElement('button');
            removeButton.classList.add('btn', 'btn-danger', 'remove-attachment-button');
            removeButton.innerHTML = 'X';

            // Remove file when clicking "X"
            removeButton.addEventListener('click', function() {
                const fileIndex = window.uploadedFiles.indexOf(file);
                if (fileIndex > -1) {
                    window.uploadedFiles.splice(fileIndex, 1); // Remove from array
                    updateFileInput(); // Update the file input field
                    fileDiv.remove(); // Remove from UI
                }
            });

            fileDiv.appendChild(img);
            fileDiv.appendChild(fileName);
            fileDiv.appendChild(removeButton);
            container.appendChild(fileDiv);
        };

        fileReader.readAsDataURL(file);
        window.uploadedFiles.push(file); // Add the new file to the array
    });

    function updateFileInput() {
        const newFileList = new DataTransfer();
        window.uploadedFiles.forEach(file => newFileList.items.add(file));
        event.target.files = newFileList.files; // Update input with new files
    }
});

