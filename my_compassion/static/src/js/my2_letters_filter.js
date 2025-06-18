document.addEventListener("DOMContentLoaded", function () {
  odoo.define("my_compassion.letters_filter", function (require) {
      "use strict";
    
      const { Component, mount, useState, loadFile} = owl;
      const { xml } = owl.tags;
      const ajax = require("web.ajax");
      const core = require("web.core");

        
        
        
    //const template = require("my_compassion.my2_letter_card");

      // Owl component for displaying letter cards
      class OwlLetterCard extends Component {
          static template = 'my2_letter_card';
      }

      class OwlLetterList extends Component {
            static template = xml`
            <div>
                <t t-foreach="state.letters" t-as="letter" t-key="letter.uuid">
                <t t-log="letter"/>
                <div class="col-12 mx-auto mb-2">
                    <OwlLetterCard letter="letter"/>
                </div>
            </t>
          </div>`
          ;

            static components = {OwlLetterCard};

        constructor() {
            super(...arguments);
            this.state = useState({
                letters: this.props.letters || []
            });
        }

        // Method to update the letters (and thereby re-render the component)
        updateLetters(newLetters) {
            this.state.letters = newLetters;
        }
      }


      // Fetch letters from the backend
      async function importLetter(childId, $container) {
          try {
              const result = await ajax.jsonRpc(`/my2/children/${childId}/get_letters`, "call", {});
              if (result && result.letters) {
                  return result.letters;
              }
          } catch (error) {
              console.error("Ajax error:", error);
              $container.html(
                  '<p class="text-danger text-center">Error loading letters</p>'
              );
          }
          return [];
      }

      // Initialize and mount the component
      async function initializeComponent() {
              const fs = require("fs");
      fs.readFile('../xml/my2_letter_card.xml',(err, data) =>{
        if (err) throw err;
        console.log(data.toString());
      });

          const $container = $(".my2-letters-container");
          // You may want to get childId from a global variable or DOM
          const childId = $container.attr("data-child-id");
          let letters = await importLetter(childId, $container);
          let owlLetterList;
          

           if (letters.length > 0) {

                owlLetterList = await mount(OwlLetterList, {
                  target: $container[0],
                  props: { letters: letters },
              }); 
          }
      }


      // Call the initialization
      initializeComponent().then(() => {
          console.log("Owl component mounted successfully.");
      }).catch((error) => {
          console.error("Error mounting Owl component:", error);
      });

  });
});