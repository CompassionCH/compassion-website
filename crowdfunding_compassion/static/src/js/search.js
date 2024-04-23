$(document).ready(function () {
  "use strict";
  $("#myInput").on("keyup", function () {
    var value = $(this).val().toLowerCase();
    var items = $(".card");
    // Show only those matching user input:
    items.filter(function () {
      var is_show = $(this).text().toLowerCase().indexOf(value) > -1;
      if (!is_show) {
        $(this).parent().css("display", "none");
      } else {
        $(this).parent().css("display", "block");
      }
    });
  });
  $("#searchInputParticipant").on("keyup", function () {
    var value = $(this).val().toLowerCase();
    var items = $(".card");
    // Show only those matching user input:
    items.filter(function () {
      var is_show = $(this).text().toLowerCase().indexOf(value) > -1;
      if (!is_show) {
        $(this).css("display", "none");
      } else {
        $(this).css("display", "block");
      }
    });
  });
});
