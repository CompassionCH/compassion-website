// Global variables

// The images compressed
let images_comp = [];
// The list of images actually displayed inside the view
let images_list = [];
// The new non-duplicated images to add to the view
let new_images = [];

let loading = false;

// Consts
const max_size = 1000;
const hard_max_size_limit = 1e7;
const resize_limit = 2e5;

const file_selector = document.getElementById("file_selector");
const image_display_table = document.getElementById("image_display_table");
const letter_content = document.getElementById("letter_content");
const canvas = document.createElement("canvas");

const template_images = document.getElementsByClassName("template-image");
const template_id = document.getElementById("template_id");

const generator_id = sessionStorage.getItem("generator_id");

function selectTemplate(selected_template_id) {
  // Change url to display selected template
  const search_params = new URLSearchParams(window.location.search);
  search_params.set("template_id", selected_template_id);
  const url =
    window.location.origin +
    window.location.pathname +
    "?" +
    search_params.toString();
  history.replaceState({}, document.title, url);

  // Convert HTMLCollection to an array to use forEach
  const templateImagesArray = Array.from(template_images);

  // Unselect all
  templateImagesArray.forEach((template_image) => {
    template_image.classList.remove("border", "border-5", "border-primary");
  });

  // Select the one
  const selected_template_image = document.getElementById(
    "template-image-" + selected_template_id
  );
  selected_template_image.classList.add("border", "border-5", "border-primary");

  template_id.innerHTML = selected_template_id;
}

selectTemplate(template_id.innerHTML);

function load_auto_text(child_id) {
  const el = document.getElementById("auto_text_" + child_id);
  if (el) {
    letter_content.value = el.innerHTML;
  }
}
load_auto_text(new URLSearchParams(window.location.search).get("child_id"));

// Add listener on child change to load the auto text
for (let i = 0; i < document.getElementsByClassName("child-card").length; i++) {
  const child_card = child_cards[i];
  child_card.addEventListener("click", function () {
    load_auto_text(child_card.dataset.childid);
  });
}

/**
 * This function compresses images that are too big by shrinking them and if
 * necessary compressing using JPEG
 * @param image the image to compress
 * @returns {Promise<unknown>} the image as a promised blob (to allow
 * asynchronous calls)
 */
async function compressImage(image) {
  const width = image.width;
  const height = image.height;

  // Calculate the width and height, constraining the proportions
  const min_width = Math.min(width, max_size);
  const min_height = Math.min(height, max_size);
  const factor = Math.min(min_width / width, min_height / height);

  // Resize the canvas and draw the image data into it
  canvas.width = Math.floor(width * factor);
  canvas.height = Math.floor(height * factor);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

  return await new Promise((resolve) =>
    ctx.canvas.toBlob(resolve, "image/jpeg")
  );
}

/**
 * Returns the index of the file in the array object, given some of its
 * characteristics
 * @param name the name of the file
 * @param size the size of the file
 * @param type the type of the file
 * @returns {Number} the index if found or -1, else
 */
Array.prototype.indexOfFile = function (name, size, type) {
  for (let i = 0; i < this.length; i++) {
    const f = this[i];
    if (f.name === name && f.size === size && f.type === type) {
      return i;
    }
  }
  return -1;
};

/**
 * Check whether a file is contained in the array object
 * @param name the name of the file
 * @param size the size of the file
 * @param type the type of the file
 * @returns {Boolean} true if the file is contained in the array or false
 */
Array.prototype.containsFile = function (name, size, type) {
  return this.indexOfFile(name, size, type) !== -1;
};

/**
 * Remove the file of the array object, or does nothing if it is not contained
 * @param name the name of the file
 * @param size the size of the file
 * @param type the type of the file
 */
function removeFile(name, size, type) {
  if (images_list.containsFile(name, size, type)) {
    const index = images_list.indexOfFile(name, size, type);
    images_list.splice(index, 1);
    images_comp.splice(index, 1);
  }
}

/**
 * Remove the image from the array as well as the HTML page
 * @param name the name of the file
 * @param size the size of the file
 * @param type the type of the file
 */
function removeImage(name, size, type) {
  removeFile(name, size, type);
  document.getElementById(`${name}_${size}_${type}`).remove();
}

function displayAlert(id) {
  $(`#${id}`).show("slow");
  setTimeout(function () {
    $(`#${id}`).hide("slow");
  }, 7000);
}

/**
 * Display the images contained in new_images inside the HTML page
 */
function displayImages() {
  // We use the images stored in the new_images array
  new_images.forEach((original_image) => {
    if (original_image.size > hard_max_size_limit) {
      displayAlert("image_too_large");
      return;
    }

    const reader = new FileReader();
    reader.onload = function (event) {
      const image = new Image();
      image.src = event.target.result;
      image.onload = function (event) {
        if (
          original_image.size > resize_limit ||
          original_image.type.valueOf() !== "image/jpeg"
        ) {
          compressImage(image).then((blob) => {
            const compressReader = new FileReader();
            compressReader.onload = function (t_event) {
              const final_data = {
                name: original_image.name,
                data: t_event.target.result.split(",")[1],
              };
              images_comp = images_comp.concat(final_data);
            };
            compressReader.readAsDataURL(blob);
          });
        } else {
          const final_data = {
            name: original_image.name,
            data: image.src.split(",")[1],
          };
          images_comp = images_comp.concat(final_data);
        }

        image_display_table.innerHTML += `
                    <div id="${original_image.name}_${original_image.size}_${original_image.type}" class="w-100">
                        <li class="embed-responsive-item p-2" style="position: relative;">
                            <span class="close close-image p-2" onclick="removeImage('${original_image.name}', ${original_image.size}, '${original_image.type}');">&times;</span>
                            <img class="text-center" src="${image.src}" alt="${original_image.name}" style="width: 100%; height: auto;"/>
                        </li>
                    </div>
                `;
      };
    };
    reader.readAsDataURL(original_image);
  });

  new_images = [];
}

/**
 * Handle the addition of new images and ignore the duplications
 * @param event the event containing the file, among other things
 */
function updateImageDisplay(event) {
  const input_images = event.target.files;

  Array.from(input_images).forEach((file) => {
    const is_image = file.type.startsWith("image/");

    if (
      is_image &&
      !images_list.containsFile(file.name, file.size, file.type)
    ) {
      new_images = new_images.concat(file);
      images_list = images_list.concat(file);
    }
  });
  displayImages();
}
file_selector.addEventListener("change", updateImageDisplay);

/**
 * Starts and end the loading of the type elements
 * @param type the type of elements to start or stop loading
 */
function startStopLoading(type) {
  loading = !loading;
  $("button").attr("disabled", loading);
  if (loading) {
    document.getElementById(`${type}_normal`).style.display = "none";
    document.getElementById(`${type}_loading`).style.display = "";
  } else {
    document.getElementById(`${type}_loading`).style.display = "none";
    document.getElementById(`${type}_normal`).style.display = "";
  }
}

/**
 * Create a new letter object in the database
 * @param preview boolean to determine whether we want to see the preview
 * @param with_loading determines whether we want to have a loading or not
 * we can send a letter directly if the user pressed the corresponding button
 */
async function createLetter(mode = "preview") {
  startStopLoading(mode);
  const params = new URLSearchParams(window.location.search);

  const json_data = {
    body: letter_content.value,
    template_id: params.get("template_id"),
    source: "mycompassion",
    generator_id: generator_id,
    csrf_token: odoo.csrf_token,
  };
  if (images_comp.length > 0) {
    json_data.file_upl = images_comp;
  }
  // Send the json data to odoo using a post request
  $.ajax({
    url: `${window.location.origin}/my/letter/${params.get(
      "child_id"
    )}/${mode}`,
    type: "POST",
    contentType: "application/json",
    data: JSON.stringify(json_data),
    success: function (response, status) {
      startStopLoading(mode);
      if (status !== "success" || response.error !== undefined) {
        displayAlert(`${mode}_error`);
        return;
      }
      if (mode === "preview") {
        sessionStorage.setItem("generator_id", response.result.generator_id);
        window.open(response.result.preview_url, "_blank");
      } else if (mode === "send") {
        // Empty images and text (to avoid duplicate)
        letter_content.value = "";
        images_list.forEach((image) => {
          removeImage(image.name, image.size, image.type);
        });
        $("#view_my_letter").attr("href", response.result.preview_url);
        $("#letter_sent_correctly").modal("show");
        $(".christmas_action").toggleClass("d-none");
        sessionStorage.removeItem("generator_id");
      }
    },
    error: function (error) {
      startStopLoading(mode);
      displayAlert(`${mode}_error`);
    },
  });
}
