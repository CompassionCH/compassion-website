/**
 * Handles the uploaded attachments from the user when filling the new letter form
 *
 * Is used in /templates/pages/my2_new_letter.xml
 */
document.getElementById('letter-attachments').addEventListener('change', function(event) {
    // Get the list of files selected by the user
    const files = event.target.files;

    // Select the container where uploaded files will be displayed
    const container = document.getElementById('uploaded-files-container');

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

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
            removeButton.classList.add('btn', 'btn-danger', 'remove-attachment-button')
            removeButton.innerHTML = 'X';

            // Add an event listener to the remove button
            removeButton.addEventListener('click', function() {
                fileDiv.remove(); // Remove the fileDiv from the DOM
            });

            // Append the img, p, button to the fileDiv
            fileDiv.appendChild(img);
            fileDiv.appendChild(fileName);
            fileDiv.appendChild(removeButton);

            // Append the fileDiv to the container to display the file
            container.appendChild(fileDiv);
        };

        // Read the file as a data URL
        fileReader.readAsDataURL(file);
    }
});
