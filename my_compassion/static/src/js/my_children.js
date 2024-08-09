const child_cards = document.getElementsByClassName("child-card");
const child_images = document.getElementsByClassName("child-image");
const child_name = document.getElementsByClassName("child-name");
const child_local_id = document.getElementsByClassName("child-local_id");

// Change the href of the links to include the child_id
const current_child_id = new URLSearchParams(window.location.search).get(
    "child_id"
);
selector = document.querySelector('a[href="/my/letter"]');
selector.href = selector.href + "?child_id=" + current_child_id;
selector = document.querySelector('a[href="/my/children"]');
selector.href = selector.href + "?child_id=" + current_child_id;

function selectChild(selected_child_id, reload) {
  // Change url to display selected child
  const search_params = new URLSearchParams(window.location.search);
  search_params.set("child_id", selected_child_id);
  const url =
    window.location.origin +
    window.location.pathname +
    "?" +
    search_params.toString();
  history.replaceState({}, document.title, url);

  // On some pages, its easier to reload the page with the right url
  if (reload) {
    window.location = url;
    // Since the page reload is slow don't update the UI before the reload
    return;
  }

  // Unselect all
  for (let i = 0; i < child_cards.length; i++) {
    const child_image = child_images[i];
    child_image.classList.remove("border", "border-5", "border-primary");
    child_image.style.opacity = 0.7;

    child_name[i].style.fontWeight = "normal";
    child_local_id[i].style.fontWeight = "normal";
  }

  // Select the one
  const selected_child_image = document.getElementById(
    "child-image-" + selected_child_id
  );
  selected_child_image.classList.add("border", "border-5", "border-primary");
  selected_child_image.style.opacity = 1;

  document.getElementById("child-name-" + selected_child_id).style.fontWeight =
    "bold";
  document.getElementById(
    "child-local_id-" + selected_child_id
  ).style.fontWeight = "bold";

  // Scroll smoothly to selected child
  const card = document.getElementById("child-card-" + selected_child_id);
  card.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
    inline: "start",
  });
}

const params = new URLSearchParams(window.location.search);
selectChild(params.get("child_id"), false);

function displayAlert(id) {
  $(`#${id}`).show("slow");
  setTimeout(function () {
    $(`#${id}`).hide("slow");
  }, 7000);
}
