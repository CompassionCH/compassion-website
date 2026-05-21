import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CrowdfundingProjectSearch = publicWidget.Widget.extend({
  selector: "#myInput",
  events: {
    keyup: "_onSearch",
  },

  _onSearch: function () {
    const value = String(this.$el.val() || "").toLowerCase();
    const items = $(".card");
    items.each(function () {
      const isVisible = $(this).text().toLowerCase().includes(value);
      $(this)
        .parent()
        .css("display", isVisible ? "block" : "none");
    });
  },
});

publicWidget.registry.CrowdfundingParticipantSearch = publicWidget.Widget.extend({
  selector: "#searchInputParticipant",
  events: {
    keyup: "_onSearch",
  },

  _onSearch: function () {
    const value = String(this.$el.val() || "").toLowerCase();
    const items = $(".card");
    items.each(function () {
      const isVisible = $(this).text().toLowerCase().includes(value);
      $(this).css("display", isVisible ? "block" : "none");
    });
  },
});
